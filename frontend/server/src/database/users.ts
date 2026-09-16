import { randomUUID } from "node:crypto";
import type { Pool, QueryResultRow } from "pg";
import { databasePool, requireDatabase } from "./pool.js";
import type { UserRecord, UserStatus } from "./models.js";

export type UserIdentityInput = {
  keycloakSubject: string;
  email?: string | null;
  username?: string | null;
  displayName?: string | null;
};

export type UpdateUserInput = {
  email?: string | null;
  username?: string | null;
  displayName?: string | null;
  status?: UserStatus;
};

type UserRow = QueryResultRow & {
  id: string;
  keycloak_subject: string;
  email: string | null;
  username: string | null;
  display_name: string | null;
  status: UserStatus;
  created_at: Date;
  updated_at: Date;
  last_login_at: Date | null;
};

function requiredSubject(value: string): string {
  const subject = value.trim();
  if (!subject) throw new Error("keycloakSubject is required");
  return subject;
}

function userFromRow(row: UserRow): UserRecord {
  return {
    id: row.id,
    keycloakSubject: row.keycloak_subject,
    email: row.email,
    username: row.username,
    displayName: row.display_name,
    status: row.status,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
    lastLoginAt: row.last_login_at,
  };
}

const userColumns = `id, keycloak_subject, email, username, display_name,
  status, created_at, updated_at, last_login_at`;

export class UserRepository {
  constructor(private readonly pool: Pool = requireDatabase()) {}

  async upsertFromKeycloak(input: UserIdentityInput): Promise<UserRecord> {
    const subject = requiredSubject(input.keycloakSubject);
    const result = await this.pool.query<UserRow>(
      `INSERT INTO users
         (id, keycloak_subject, email, username, display_name, last_login_at)
       VALUES ($1, $2, $3, $4, $5, now())
       ON CONFLICT (keycloak_subject) DO UPDATE SET
         email = EXCLUDED.email,
         username = EXCLUDED.username,
         display_name = EXCLUDED.display_name,
         last_login_at = now()
       RETURNING ${userColumns}`,
      [
        randomUUID(),
        subject,
        input.email?.trim() || null,
        input.username?.trim() || null,
        input.displayName?.trim() || null,
      ],
    );
    const row = result.rows[0];
    if (!row) throw new Error("User upsert returned no row");
    return userFromRow(row);
  }

  async findById(id: string): Promise<UserRecord | null> {
    const result = await this.pool.query<UserRow>(
      `SELECT ${userColumns} FROM users WHERE id = $1`,
      [id],
    );
    return result.rows[0] ? userFromRow(result.rows[0]) : null;
  }

  async findByKeycloakSubject(keycloakSubject: string): Promise<UserRecord | null> {
    const result = await this.pool.query<UserRow>(
      `SELECT ${userColumns} FROM users WHERE keycloak_subject = $1`,
      [requiredSubject(keycloakSubject)],
    );
    return result.rows[0] ? userFromRow(result.rows[0]) : null;
  }

  async update(id: string, input: UpdateUserInput): Promise<UserRecord | null> {
    const result = await this.pool.query<UserRow>(
      `UPDATE users
       SET email = CASE WHEN $2::boolean THEN $3::text ELSE email END,
           username = CASE WHEN $4::boolean THEN $5::text ELSE username END,
           display_name = CASE WHEN $6::boolean THEN $7::text ELSE display_name END,
           status = COALESCE($8, status)
       WHERE id = $1
       RETURNING ${userColumns}`,
      [
        id,
        input.email !== undefined,
        input.email === undefined ? null : input.email?.trim() || null,
        input.username !== undefined,
        input.username === undefined ? null : input.username?.trim() || null,
        input.displayName !== undefined,
        input.displayName === undefined ? null : input.displayName?.trim() || null,
        input.status ?? null,
      ],
    );
    return result.rows[0] ? userFromRow(result.rows[0]) : null;
  }
}

export function userRepository(): UserRepository {
  return new UserRepository(databasePool ?? requireDatabase());
}
