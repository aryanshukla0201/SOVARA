import { createHash, randomBytes } from "node:crypto";
import { createRemoteJWKSet, jwtVerify, type JWTPayload } from "jose";
import { authConfig } from "./config.js";

type OidcDiscovery = {
  authorization_endpoint: string;
  token_endpoint: string;
  userinfo_endpoint?: string;
  end_session_endpoint?: string;
  jwks_uri: string;
};

export type IdentityClaims = {
  subject: string;
  email: string | null;
  username: string | null;
  displayName: string | null;
};

let discoveryPromise: Promise<OidcDiscovery> | undefined;
let jwks: ReturnType<typeof createRemoteJWKSet> | undefined;

async function discover(): Promise<OidcDiscovery> {
  const response = await fetch(`${authConfig.issuer}/.well-known/openid-configuration`);
  if (!response.ok) throw new Error(`Keycloak discovery failed: HTTP ${response.status}`);
  const value = (await response.json()) as Partial<OidcDiscovery>;
  if (!value.authorization_endpoint || !value.token_endpoint || !value.jwks_uri) {
    throw new Error("Keycloak discovery response is incomplete");
  }
  return value as OidcDiscovery;
}

async function getDiscovery(): Promise<OidcDiscovery> {
  discoveryPromise ??= discover().catch((error) => {
    discoveryPromise = undefined;
    throw error;
  });
  return discoveryPromise;
}

function base64Url(value: Buffer): string {
  return value.toString("base64url");
}

export function randomToken(bytes = 32): string {
  return base64Url(randomBytes(bytes));
}

export function createPkcePair(): { verifier: string; challenge: string } {
  const verifier = randomToken(48);
  const challenge = base64Url(createHash("sha256").update(verifier).digest());
  return { verifier, challenge };
}

export async function createAuthorizationUrl(input: {
  state: string;
  nonce: string;
  challenge: string;
}): Promise<string> {
  const discovery = await getDiscovery();
  const url = new URL(discovery.authorization_endpoint);
  url.search = new URLSearchParams({
    client_id: authConfig.clientId,
    redirect_uri: authConfig.redirectUri,
    response_type: "code",
    scope: "openid profile email",
    state: input.state,
    nonce: input.nonce,
    code_challenge: input.challenge,
    code_challenge_method: "S256",
  }).toString();
  return url.toString();
}

async function exchangeCode(code: string, verifier: string): Promise<{
  id_token: string;
  access_token?: string;
}> {
  if (!authConfig.clientSecret) {
    throw new Error("KEYCLOAK_CLIENT_SECRET is required before login can start");
  }
  const discovery = await getDiscovery();
  const response = await fetch(discovery.token_endpoint, {
    method: "POST",
    headers: { "content-type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "authorization_code",
      client_id: authConfig.clientId,
      client_secret: authConfig.clientSecret,
      redirect_uri: authConfig.redirectUri,
      code,
      code_verifier: verifier,
    }),
  });
  if (!response.ok) throw new Error(`Keycloak token exchange failed: HTTP ${response.status}`);
  const value = (await response.json()) as { id_token?: string; access_token?: string };
  if (!value.id_token) throw new Error("Keycloak token response did not contain an ID token");
  return value as { id_token: string; access_token?: string };
}

function claimString(payload: JWTPayload, key: string): string | null {
  const value = payload[key];
  return typeof value === "string" && value.length > 0 ? value : null;
}

export async function authenticateCode(input: {
  code: string;
  verifier: string;
  nonce: string;
}): Promise<IdentityClaims> {
  const tokens = await exchangeCode(input.code, input.verifier);
  const discovery = await getDiscovery();
  jwks ??= createRemoteJWKSet(new URL(discovery.jwks_uri));
  const { payload } = await jwtVerify(tokens.id_token, jwks, {
    issuer: authConfig.issuer,
    audience: authConfig.clientId,
  });
  if (payload.nonce !== input.nonce) throw new Error("Keycloak nonce validation failed");
  if (!payload.sub) throw new Error("Keycloak identity did not contain a subject");

  let profile: Record<string, unknown> = {};
  if (tokens.access_token && discovery.userinfo_endpoint) {
    const response = await fetch(discovery.userinfo_endpoint, {
      headers: { authorization: `Bearer ${tokens.access_token}` },
    });
    if (response.ok) profile = (await response.json()) as Record<string, unknown>;
  }

  const merged = { ...payload, ...profile } as JWTPayload & Record<string, unknown>;
  const displayName =
    (typeof merged.name === "string" && merged.name) ||
    (typeof merged.preferred_username === "string" && merged.preferred_username) ||
    null;
  return {
    subject: payload.sub,
    email: typeof merged.email === "string" ? merged.email : null,
    username: typeof merged.preferred_username === "string" ? merged.preferred_username : null,
    displayName,
  };
}

export async function createLogoutUrl(idTokenHint?: string): Promise<string | null> {
  const discovery = await getDiscovery();
  if (!discovery.end_session_endpoint) return null;
  const url = new URL(discovery.end_session_endpoint);
  url.search = new URLSearchParams({
    client_id: authConfig.clientId,
    post_logout_redirect_uri: authConfig.postLogoutRedirectUri,
    ...(idTokenHint ? { id_token_hint: idTokenHint } : {}),
  }).toString();
  return url.toString();
}
