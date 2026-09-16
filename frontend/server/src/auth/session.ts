import { createHash } from "node:crypto";
import type { Request, Response } from "express";
import { authConfig } from "./config.js";
import { randomToken, type IdentityClaims } from "./oidc.js";
import { databaseConfigured } from "../database/pool.js";
import { databaseSessionStore } from "./session-store.js";

export const SESSION_COOKIE = "__Host-sovara_session";

export type ApplicationSession = IdentityClaims & {
  sessionId: string;
  csrfToken: string;
  createdAt: number;
  expiresAt: number;
  applicationUserId: string | null;
  organizationId: string | null;
  role: string | null;
  permissions: readonly string[];
};

const sessions = new Map<string, ApplicationSession>();

function cookieAttributes(): string {
  return [
    `${SESSION_COOKIE}=`,
    "Path=/",
    "HttpOnly",
    "SameSite=Lax",
    ...(authConfig.sessionCookieSecure ? ["Secure"] : []),
  ].join("; ");
}

export function csrfTokenForSession(sessionToken: string): string {
  return createHash("sha256").update(`${sessionToken}:csrf`).digest("hex");
}

export function createSession(
  identity: IdentityClaims,
  applicationContext: {
    userId?: string | null;
    organizationId?: string | null;
    role?: string | null;
    permissions?: readonly string[];
  } = {},
): ApplicationSession {
  const now = Date.now();
  const sessionToken = randomToken(32);
  const session: ApplicationSession = {
    ...identity,
    sessionId: sessionToken,
    csrfToken: csrfTokenForSession(sessionToken),
    createdAt: now,
    expiresAt: now + authConfig.sessionTtlMs,
    applicationUserId: applicationContext.userId ?? null,
    organizationId: applicationContext.organizationId ?? null,
    role: applicationContext.role ?? null,
    permissions: applicationContext.permissions ?? [],
  };
  sessions.set(session.sessionId, session);
  return session;
}

function rawSessionToken(request: Request): string | null {
  const raw = request.headers.cookie?.match(new RegExp(`(?:^|;\\s*)${SESSION_COOKIE}=([^;]+)`))?.[1];
  return raw ? decodeURIComponent(raw) : null;
}

export async function getSession(request: Request): Promise<ApplicationSession | null> {
  const token = rawSessionToken(request);
  if (!token) return null;
  if (databaseConfigured) {
    const stored = await databaseSessionStore().find(token);
    if (!stored) return null;
    return {
      ...stored.identity,
      sessionId: stored.token,
      csrfToken: csrfTokenForSession(stored.token),
      createdAt: stored.createdAt,
      expiresAt: stored.expiresAt,
      applicationUserId: stored.userId,
      organizationId: null,
      role: null,
      permissions: [],
    };
  }
  const session = sessions.get(token);
  if (!session || session.expiresAt <= Date.now()) {
    if (session) sessions.delete(token);
    return null;
  }
  return session;
}

export async function createApplicationSession(
  identity: IdentityClaims,
  applicationContext: {
    userId?: string | null;
    organizationId?: string | null;
    role?: string | null;
    permissions?: readonly string[];
  } = {},
  requestContext: { ipAddress?: string | null; userAgent?: string | null } = {},
): Promise<ApplicationSession> {
  const session = createSession(identity, applicationContext);
  if (databaseConfigured) {
    if (!session.applicationUserId) throw new Error("Database sessions require an application user");
    await databaseSessionStore().create({
      token: session.sessionId,
      userId: session.applicationUserId,
      identity,
      expiresAt: session.expiresAt,
      ipAddress: requestContext.ipAddress ?? null,
      userAgent: requestContext.userAgent ?? null,
    });
  }
  return session;
}

export function setSessionCookie(response: Response, sessionId: string): void {
  response.setHeader(
    "Set-Cookie",
    `${SESSION_COOKIE}=${encodeURIComponent(sessionId)}; Path=/; HttpOnly; SameSite=Lax${
      authConfig.sessionCookieSecure ? "; Secure" : ""
    }`,
  );
}

export function clearSessionCookie(response: Response): void {
  response.setHeader("Set-Cookie", `${cookieAttributes()} Max-Age=0`);
}

export async function deleteSession(session: ApplicationSession): Promise<void> {
  sessions.delete(session.sessionId);
  if (databaseConfigured) await databaseSessionStore().revoke(session.sessionId);
}

export function hasValidCsrfToken(session: ApplicationSession, value: unknown): boolean {
  return typeof value === "string" && value.length > 0 && value === session.csrfToken;
}

export function cleanupExpiredSessions(): void {
  const now = Date.now();
  for (const [id, session] of sessions) {
    if (session.expiresAt <= now) sessions.delete(id);
  }
}

setInterval(cleanupExpiredSessions, 60_000).unref();
