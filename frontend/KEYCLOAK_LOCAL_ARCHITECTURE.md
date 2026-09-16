# Local Keycloak Authentication Architecture

## 1. Purpose

This document describes how to use Keycloak locally as the identity provider
while keeping the application's own frontend and backend responsible for the
user experience and application security.

The intended model is:

- React/TanStack Start remains the user-facing frontend.
- The application backend is the only component that communicates with
  Keycloak during normal sign-in.
- Keycloak provides identity, authentication, sessions, roles, and token
  issuance.
- Application data APIs remain behind the application backend.
- The browser receives an application session cookie, not a Keycloak client
  secret and preferably not a long-lived access token.

This is a target architecture. The current project is already wired to Better
Auth and Grok-specific authentication. Keycloak should be introduced as an
explicit migration, not mixed into the existing auth implementation without a
clear ownership decision.

## 2. High-Level Architecture

```text
+-------------------+       HTTPS        +-------------------------+
|                   | ------------------> |                         |
|  Custom frontend  |                     |  Application backend    |
|  React/TanStack   | <------------------ |  BFF / API / SSR        |
|                   |   HttpOnly cookie  |                         |
+-------------------+                    +------------+------------+
                                                     |
                                  OIDC Authorization  |  Code + PKCE
                                  and token exchange  |
                                                     v
                                           +-------------------------+
                                           |        Keycloak         |
                                           | Realm, users, roles,    |
                                           | clients, identity       |
                                           | provider and sessions   |
                                           +-------------------------+

                                           +-------------------------+
                                           | Application database    |
                                           | Users, domain data,     |
                                           | external subject IDs    |
                                           +-------------------------+
```

### Component responsibilities

| Component | Responsibility | Must not do |
|---|---|---|
| Frontend | Render login, callback states, protected screens, and logout controls | Store client secrets or decide authorization using only client-side state |
| Application backend | Start OIDC, exchange the code, validate identity, create the app session, enforce authorization, and serve APIs | Trust a user ID sent by the browser |
| Keycloak | Authenticate users, manage realm users and roles, issue and revoke tokens, and expose OIDC metadata | Own application business data or application-specific UI |
| Application database | Store domain records and a mapping to the Keycloak subject (`sub`) | Store raw passwords or unnecessary Keycloak tokens |
| Browser | Hold a secure application session cookie | Hold refresh tokens in localStorage or sessionStorage |

## 3. Recommended Authentication Protocol

Use OpenID Connect on top of OAuth 2.0 with the Authorization Code flow and
PKCE (`S256`). Use a confidential Keycloak client for the backend.

The frontend should initiate login by navigating to the backend, for example:

```text
GET /api/auth/login?returnTo=/workbench
```

The backend generates and stores a short-lived `state`, `nonce`, and PKCE
verifier, then redirects the browser to Keycloak. The backend handles the
callback and exchanges the authorization code directly with Keycloak.

The frontend therefore uses its own UI, while Keycloak still performs the
credential and identity step. If a fully custom credential form is required,
do not collect the user's Keycloak password in the application. Prefer the
OIDC redirect flow; custom Keycloak themes are the safer way to customize the
credential screen itself.

## 4. Local Network and URLs

Recommended local URLs:

```text
Application: http://localhost:8080
Keycloak:    http://localhost:8081
Realm:       http://localhost:8081/realms/sovara-local
Discovery:   http://localhost:8081/realms/sovara-local/.well-known/openid-configuration
```

The Keycloak URL must be consistent everywhere. Do not mix `localhost` and
`127.0.0.1` in redirect URIs, cookies, or environment values unless both are
deliberately configured. For normal browser development, use one hostname
consistently.

## 5. Keycloak Local Configuration

Create a dedicated local realm instead of using the `master` realm:

```text
Realm: sovara-local
```

Create a backend OIDC client:

```text
Client ID:              sovara-backend-local
Client type:            OpenID Connect
Client authentication:  On (confidential client)
Standard flow:          On
Direct access grants:   Off
Implicit flow:          Off
Valid redirect URI:     http://localhost:8080/api/auth/callback/keycloak
Web origins:            http://localhost:8080
```

The client secret belongs only in the backend environment. Never expose it as
a `VITE_` variable or include it in browser JavaScript.

Create application roles deliberately. A starting set could be:

```text
user
operator
admin
```

Use realm roles for roles shared across many clients. Use client roles for
roles specific to this application. Keep authorization decisions in the
backend, and use frontend roles only to control presentation and navigation.

For backend-to-backend calls, create a separate confidential service-account
client. Do not reuse the interactive browser client for machine credentials.

## 6. Login Flow

1. The user clicks the custom frontend's Sign in button.
2. The frontend navigates to `GET /api/auth/login`.
3. The backend generates `state`, `nonce`, and PKCE values and stores the
   transaction server-side with a short expiration.
4. The backend redirects the browser to Keycloak's authorization endpoint.
5. Keycloak authenticates the user and redirects to the backend callback.
6. The backend verifies `state` and exchanges the code using the PKCE verifier
   and client secret.
7. The backend validates the ID token's issuer, signature, expiration, nonce,
   and audience.
8. The backend maps the Keycloak `sub` to an application user record.
9. The backend creates an application session and sends a cookie such as:

   ```text
   __Host-sovara_session=<opaque-server-side-session>
   ```

10. The backend redirects the browser to the validated `returnTo` location.
11. The frontend calls `GET /api/auth/session` to render the current user.

The recommended session cookie is opaque. Keep access and refresh tokens on the
server, encrypted at rest if they must be persisted. Do not put tokens in
localStorage.

## 7. Request and Authorization Flow

For every protected backend endpoint:

1. Read the application session cookie.
2. Load the session server-side.
3. Reject missing, expired, or revoked sessions with HTTP `401`.
4. Resolve the application user from the verified Keycloak `sub`.
5. Check the required role or permission server-side.
6. Scope database queries by the authenticated application user or tenant.
7. Return only the data authorized for that user.

The backend must never accept `userId`, `role`, `tenantId`, or ownership fields
from the browser as proof of authorization. Client-provided values can be
inputs, but the server must compare them with the verified session and its own
authorization rules.

Suggested endpoint contract:

```text
GET  /api/auth/login?returnTo=/workbench
GET  /api/auth/callback/keycloak?code=...&state=...
POST /api/auth/logout
GET  /api/auth/session
GET  /api/auth/csrf
```

The callback should not be called directly by frontend JavaScript. It should be
a browser redirect target handled by the backend.

## 8. Logout Flow

`POST /api/auth/logout` should:

1. Require the application session.
2. Revoke or invalidate the local session immediately.
3. Clear the application cookie.
4. Optionally redirect the browser through Keycloak's end-session endpoint to
   clear the Keycloak SSO session.

Use a registered `post_logout_redirect_uri` and a validated `client_id`. Never
redirect to an arbitrary URL supplied by the browser.

## 9. Token Validation

The backend must validate tokens using Keycloak's realm issuer and JWKS:

```text
Issuer:   http://localhost:8081/realms/sovara-local
JWKS:     <issuer>/.well-known/openid-configuration -> jwks_uri
Audience: sovara-backend-local
```

Required checks include:

- Signature against Keycloak's current JWKS key
- `iss` equals the configured realm issuer
- `aud` or `azp` matches the expected client
- `exp` has not passed
- `iat` is reasonable
- `nonce` matches the login transaction for ID tokens
- `state` matches the login transaction for the callback
- Required scopes and roles are present

Cache JWKS keys briefly and refresh them when Keycloak rotates signing keys.
Do not disable issuer, audience, TLS, or signature checks to make local setup
work.

For this browser-facing BFF design, the application session is the normal API
credential. Direct bearer-token APIs are only needed when separate services
must be called independently. In that case, each service validates the token
and its audience itself; it must not trust validation performed by another
service.

## 10. Cookie, CSRF, and Browser Security

Configure the application session cookie with:

```text
HttpOnly
Secure       # use HTTPS outside localhost development
SameSite=Lax
Path=/
No Domain attribute
```

Use `__Host-` naming in production when the cookie is scoped to the application
host. Rotate the session ID after login to prevent session fixation.

Because cookie-authenticated state-changing requests are vulnerable to CSRF:

- Require a CSRF token for state-changing requests, or use a validated
  same-origin anti-CSRF mechanism.
- Validate the `Origin` header for browser requests.
- Restrict CORS to the exact frontend origin if the frontend and backend are
  on different origins.
- Do not use `Access-Control-Allow-Origin: *` with credentials.
- Reject unexpected methods and content types on auth endpoints.

Add security headers at the backend or reverse proxy, including a restrictive
Content Security Policy, `frame-ancestors`, `Referrer-Policy`, and
`X-Content-Type-Options`. Avoid allowing the login and callback endpoints to
be framed.

## 11. Environment Variables

Keep these variables server-only:

```env
KEYCLOAK_ISSUER=http://localhost:8081/realms/sovara-local
KEYCLOAK_CLIENT_ID=sovara-backend-local
KEYCLOAK_CLIENT_SECRET=<local-confidential-client-secret>
KEYCLOAK_REDIRECT_URI=http://localhost:8080/api/auth/callback/keycloak
KEYCLOAK_POST_LOGOUT_REDIRECT_URI=http://localhost:8080/
SESSION_SECRET=<long-random-local-secret>
DATABASE_URL=<application-database-connection>
```

Do not use the `VITE_` prefix for secrets. Vite exposes `VITE_` variables to
browser code.

Generate local secrets with a cryptographically secure generator and keep
them in an ignored `.env.local` file or an operating-system secret store. Do
not commit realm exports containing client secrets.

## 12. Local Keycloak Runtime

Run Keycloak as a local dependency, normally with a development-only Docker
Compose service. Persist its data in a named local volume if you want users
and realm configuration to survive restarts.

The local runtime should provide:

- Keycloak on `localhost:8081`
- A realm import or repeatable setup script for `sovara-local`
- A local admin account supplied through environment variables
- A health check before the application starts integration tests
- A separate local database for Keycloak if the deployment-like setup needs
  persistence

Do not expose the Keycloak admin console or admin API to the public internet.
Use a separate admin account from application test users.

## 13. Application Data Model

The application database should store a stable external identity mapping:

```text
users
  id
  keycloak_subject       unique, indexed
  email                  optional, not the primary identity key
  display_name
  created_at
  updated_at
```

Use the Keycloak `sub` claim as the identity key. Do not use email as the
permanent identity key because email addresses can change and may not be
globally unique across identity providers.

If multi-tenancy is added, map the verified subject to memberships in the
application database and enforce tenant access on every query. Keycloak roles
alone are not a replacement for application ownership and membership checks.

## 14. Frontend Integration

The custom frontend needs only application-facing calls:

```ts
window.location.assign(`/api/auth/login?returnTo=${encodeURIComponent(path)}`);

const session = await fetch("/api/auth/session", {
  credentials: "include",
}).then((response) => response.json());
```

The frontend should handle these states:

- Loading session
- Signed out
- Signed in
- Session expired
- Login cancelled
- Login failed
- Insufficient permission (`403`)

The frontend may hide or show controls based on the session response, but every
backend endpoint must repeat the authorization check. Never rely on disabled
buttons or hidden routes for security.

## 15. Mapping to This Repository

The current repository contains Better Auth and Grok-specific auth modules,
including:

```text
src/lib/auth/server.ts
src/lib/auth/verify.server.ts
src/lib/auth/middleware.ts
src/lib/auth/client.ts
src/lib/auth/gates.tsx
src/lib/auth/preview.ts
server/middleware/grok-pwa.ts
```

A Keycloak migration should define one authentication owner. The recommended
sequence is:

1. Add a backend-only Keycloak client and issuer configuration.
2. Implement a server-side OIDC client and login transaction store.
3. Implement the application session cookie and `/api/auth/session`.
4. Add backend middleware that resolves the verified Keycloak subject.
5. Migrate protected server functions and API routes to that middleware.
6. Replace the frontend auth hook and gates with calls to the application
   session endpoint.
7. Migrate user records using the Keycloak `sub` mapping.
8. Remove Better Auth/Grok auth code only after all routes and tests use
   Keycloak.

Do not run Better Auth and Keycloak as two competing sources of truth for the
same session. During a temporary migration, make the boundary explicit and
use separate routes and cookies.

## 16. Proposed Code Boundaries

The final implementation should keep responsibilities separated roughly like
this:

```text
src/lib/auth/
  keycloak-config.server.ts       # issuer, client, redirect configuration
  oidc-client.server.ts           # discovery, code exchange, JWKS validation
  login-transaction.server.ts    # state, nonce, PKCE, expiry
  session.server.ts              # opaque sessions and cookie management
  authorization.server.ts        # roles, permissions, ownership checks
  current-user.ts                # frontend-safe session types and hook

src/routes/api/auth/
  login.ts                        # redirect to Keycloak
  callback/keycloak.ts            # code exchange and session creation
  session.ts                      # current user response
  logout.ts                       # revoke local session and optionally SSO

src/server/
  auth-middleware.ts              # protected server request boundary
```

The exact TanStack Start route syntax can vary, but secrets, token exchange,
cookie signing, and token validation must remain in server-only modules.

## 17. Security Checklist

Before considering the integration complete:

- [ ] The application uses a dedicated non-`master` realm.
- [ ] The backend client is confidential and its secret is server-only.
- [ ] Authorization Code + PKCE is used.
- [ ] Direct access grants and implicit flow are disabled.
- [ ] Redirect and logout URLs are exact and allowlisted.
- [ ] `state` and `nonce` are generated, stored, checked, and expired.
- [ ] Tokens are never stored in localStorage or sessionStorage.
- [ ] Session cookies are HttpOnly, Secure where applicable, SameSite, and host-scoped.
- [ ] Session IDs rotate after login.
- [ ] CSRF and Origin checks protect state-changing cookie requests.
- [ ] Issuer, audience, signature, expiration, and nonce are validated.
- [ ] JWKS rotation is supported.
- [ ] Every protected backend route checks the verified subject and permissions.
- [ ] Database records are scoped by the authenticated user or tenant.
- [ ] Keycloak admin endpoints are not public.
- [ ] Secrets are excluded from Git and logs.
- [ ] Login, callback, logout, expired-session, and forbidden responses are tested.

## 18. Testing Plan

Test locally with a dedicated Keycloak test user and verify:

1. Signed-out access returns `401` or redirects to login as designed.
2. Login succeeds and creates only the application session cookie.
3. The callback rejects an invalid, reused, or expired `state` value.
4. The callback rejects a nonce mismatch and an invalid issuer.
5. An expired or revoked application session cannot access protected data.
6. A user without the required role receives `403`.
7. One user cannot read or mutate another user's records.
8. Logout invalidates the application session and clears the cookie.
9. Refresh-token and Keycloak outages fail closed without leaking tokens.
10. Key rotation still allows valid tokens after JWKS refresh.

Use separate browser and API integration tests. Unit tests should cover state,
nonce, PKCE, redirect validation, cookie flags, claim mapping, and permission
checks without requiring a running Keycloak instance.
