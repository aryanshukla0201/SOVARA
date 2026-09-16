import { createHash, randomUUID } from "node:crypto";
import type { Pool, QueryResultRow } from "pg";
import { databasePool, requireDatabase } from "../database/pool.js";
import type { IdentityClaims } from "./oidc.js";

export type StoredSession = {
  databaseId: string;
  token: string;
  userId: string;
  identity: IdentityClaims;
  createdAt: number;
  expiresAt: number;
};

type SessionRow = QueryResultRow & {
  session_id: string;
  user_id: string;
  keycloak_subject: string;
  email: string | null;
  username: string | null;
  display_name: string | null;
  created_at: Date;
  expires_at: Date;
};

export function hashSessionToken(token: string): string {
  return createHash("sha256").update(token).digest("hex");
}

function identityFromRow(row: SessionRow): IdentityClaims {
  return {
    subject: row.keycloak_subject,
    email: row.email,
    username: row.username,
    displayName: row.display_name,
  };
}

export class DatabaseSessionStore {
  constructor(private readonly pool: Pool = requireDatabase()) {}

  async create(input: {
    token: string;
    userId: string;
    identity: IdentityClaims;
    expiresAt: number;
    ipAddress?: string | null;
    userAgent?: string | null;
  }): Promise<StoredSession> {
    const id = randomUUID();
    const createdAt = Date.now();
    await this.pool.query(
      `INSERT INTO sessions
         (id, user_id, token_hash, expires_at, created_at, last_seen_at, ip_address, user_agent)
       VALUES ($1, $2, $3, $4, now(), now(), $5, $6)`,
      [
        id,
        input.userId,
        hashSessionToken(input.token),
        new Date(input.expiresAt),
        input.ipAddress ?? null,
        input.userAgent ?? null,
      ],
    );
    return {
      databaseId: id,
      token: input.token,
      userId: input.userId,
      identity: input.identity,
      createdAt,
      expiresAt: input.expiresAt,
    };
  }

  async find(token: string): Promise<StoredSession | null> {
    const result = await this.pool.query<SessionRow>(
      `UPDATE sessions s
       SET last_seen_at = now()
       FROM users u
       WHERE s.token_hash = $1
         AND s.user_id = u.id
         AND s.revoked_at IS NULL
         AND s.expires_at > now()
       RETURNING s.id AS session_id, s.user_id, u.keycloak_subject, u.email,
         u.username, u.display_name, s.created_at, s.expires_at`,
      [hashSessionToken(token)],
    );
    const row = result.rows[0];
    if (!row) return null;
    return {
      databaseId: row.session_id,
      token,
      userId: row.user_id,
      identity: identityFromRow(row),
      createdAt: row.created_at.getTime(),
      expiresAt: row.expires_at.getTime(),
    };
  }

  async revoke(token: string): Promise<void> {
    await this.pool.query(
      `UPDATE sessions SET revoked_at = now()
       WHERE token_hash = $1 AND revoked_at IS NULL`,
      [hashSessionToken(token)],
    );
  }
}

export function databaseSessionStore(): DatabaseSessionStore {
  return new DatabaseSessionStore(databasePool ?? requireDatabase());
}
