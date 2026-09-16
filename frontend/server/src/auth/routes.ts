import { Router, type Request } from "express";
import { authConfig, isSafeReturnTo } from "./config.js";
import { resolveApplicationIdentity } from "./application-identity.js";
import { resolveAuthContext } from "./context.js";
import {
  authenticateCode,
  createAuthorizationUrl,
  createLogoutUrl,
  createPkcePair,
  randomToken,
} from "./oidc.js";
import {
  clearSessionCookie,
  createApplicationSession,
  deleteSession,
  getSession,
  hasValidCsrfToken,
  setSessionCookie,
} from "./session.js";

type LoginTransaction = {
  state: string;
  nonce: string;
  verifier: string;
  returnTo: string;
  expiresAt: number;
};

const transactions = new Map<string, LoginTransaction>();
const router: Router = Router();

function queryString(request: Request, key: string): string | undefined {
  const value = request.query[key];
  return typeof value === "string" ? value : undefined;
}

function frontendRedirect(returnTo: string): string {
  return new URL(returnTo, authConfig.frontendOrigin).toString();
}

router.get("/api/auth/login", async (request, response, next) => {
  try {
    const requestedReturnTo = queryString(request, "returnTo") ?? "/";
    const returnTo = isSafeReturnTo(requestedReturnTo) ? requestedReturnTo : "/";
    const pkce = createPkcePair();
    const transaction: LoginTransaction = {
      state: randomToken(32),
      nonce: randomToken(32),
      verifier: pkce.verifier,
      returnTo,
      expiresAt: Date.now() + authConfig.loginTransactionTtlMs,
    };
    transactions.set(transaction.state, transaction);
    response.redirect(
      await createAuthorizationUrl({
        state: transaction.state,
        nonce: transaction.nonce,
        challenge: pkce.challenge,
      }),
    );
  } catch (error) {
    next(error);
  }
});

router.get("/api/auth/callback/keycloak", async (request, response) => {
  const code = queryString(request, "code");
  const state = queryString(request, "state");
  const transaction = state ? transactions.get(state) : undefined;
  if (!code || !state || !transaction || transaction.expiresAt <= Date.now()) {
    if (state) transactions.delete(state);
    response.status(400).json({ error: "invalid_login_callback" });
    return;
  }
  transactions.delete(state);
  try {
    const identity = await authenticateCode({
      code,
      verifier: transaction.verifier,
      nonce: transaction.nonce,
    });
    const applicationContext = await resolveApplicationIdentity(identity);
    const session = await createApplicationSession(identity, applicationContext, {
      ipAddress: request.ip ?? null,
      userAgent: request.get("user-agent") ?? null,
    });
    setSessionCookie(response, session.sessionId);
    response.redirect(frontendRedirect(transaction.returnTo));
  } catch (error) {
    console.error("[auth] Keycloak callback failed", error);
    response.status(401).json({ error: "authentication_failed" });
  }
});

router.get("/api/auth/session", async (request, response, next) => {
  const session = await getSession(request);
  if (!session) {
    response.status(401).json({ authenticated: false });
    return;
  }
  try {
    const context = await resolveAuthContext(session);
    response.json({
      authenticated: true,
      user: {
        id: context.userId ?? context.keycloakSubject,
        keycloakSubject: context.keycloakSubject,
        email: context.email,
        username: context.username,
        displayName: context.displayName,
        organizationId: context.organizationId,
        role: context.role,
        permissions: context.permissions,
      },
      csrfToken: session.csrfToken,
      expiresAt: new Date(session.expiresAt).toISOString(),
    });
  } catch (error) {
    next(error);
  }
});

router.post("/api/auth/logout", async (request, response, next) => {
  try {
    const session = await getSession(request);
    if (!session) {
      clearSessionCookie(response);
      response.status(204).end();
      return;
    }
    const csrf = request.get("x-csrf-token") ?? request.body?.csrfToken;
    if (!hasValidCsrfToken(session, csrf)) {
      response.status(403).json({ error: "csrf_validation_failed" });
      return;
    }
    await deleteSession(session);
    clearSessionCookie(response);
    const logoutUrl = await createLogoutUrl();
    if (logoutUrl) {
      response.json({ loggedOut: true, logoutUrl });
      return;
    }
    response.status(204).end();
  } catch (error) {
    next(error);
  }
});

export async function requireApplicationSession(request: Request) {
  const session = await getSession(request);
  if (!session) {
    const error = new Error("Unauthorized");
    (error as Error & { status?: number }).status = 401;
    throw error;
  }
  return session;
}

export default router;
