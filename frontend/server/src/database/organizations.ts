import { randomUUID } from "node:crypto";
import type { Pool, QueryResultRow } from "pg";
import { databasePool, requireDatabase } from "./pool.js";
import type { OrganizationRecord, OrganizationStatus } from "./models.js";

export type CreateOrganizationInput = {
  name: string;
  code: string;
  type?: string | null;
};

export type UpdateOrganizationInput = {
  name?: string;
  type?: string | null;
  status?: OrganizationStatus;
};

type OrganizationRow = QueryResultRow & {
  id: string;
  name: string;
  code: string;
  type: string | null;
  status: OrganizationStatus;
  created_at: Date;
  updated_at: Date;
};

function required(value: string | undefined, field: string): string {
  const normalized = value?.trim();
  if (!normalized) throw new Error(`${field} is required`);
  return normalized;
}

function organizationFromRow(row: OrganizationRow): OrganizationRecord {
  return {
    id: row.id,
    name: row.name,
    code: row.code,
    type: row.type,
    status: row.status,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

export class OrganizationRepository {
  constructor(private readonly pool: Pool = requireDatabase()) {}

  async create(input: CreateOrganizationInput): Promise<OrganizationRecord> {
    const name = required(input.name, "name");
    const code = required(input.code, "code").toUpperCase();
    const result = await this.pool.query<OrganizationRow>(
      `INSERT INTO organizations (id, name, code, type)
       VALUES ($1, $2, $3, $4)
       RETURNING id, name, code, type, status, created_at, updated_at`,
      [randomUUID(), name, code, input.type?.trim() || null],
    );
    const row = result.rows[0];
    if (!row) throw new Error("Organization insert returned no row");
    return organizationFromRow(row);
  }

  async findById(id: string): Promise<OrganizationRecord | null> {
    const result = await this.pool.query<OrganizationRow>(
      `SELECT id, name, code, type, status, created_at, updated_at
       FROM organizations
       WHERE id = $1`,
      [id],
    );
    return result.rows[0] ? organizationFromRow(result.rows[0]) : null;
  }

  async findByCode(code: string): Promise<OrganizationRecord | null> {
    const result = await this.pool.query<OrganizationRow>(
      `SELECT id, name, code, type, status, created_at, updated_at
       FROM organizations
       WHERE code = $1`,
      [required(code, "code").toUpperCase()],
    );
    return result.rows[0] ? organizationFromRow(result.rows[0]) : null;
  }

  async update(id: string, input: UpdateOrganizationInput): Promise<OrganizationRecord | null> {
    const result = await this.pool.query<OrganizationRow>(
      `UPDATE organizations
       SET name = COALESCE($2, name),
           type = CASE WHEN $3::boolean THEN $4::text ELSE type END,
           status = COALESCE($5, status)
       WHERE id = $1
       RETURNING id, name, code, type, status, created_at, updated_at`,
      [
        id,
        input.name === undefined ? null : required(input.name, "name"),
        input.type !== undefined,
        input.type === undefined ? null : input.type?.trim() || null,
        input.status ?? null,
      ],
    );
    return result.rows[0] ? organizationFromRow(result.rows[0]) : null;
  }
}

export function organizationRepository(): OrganizationRepository {
  return new OrganizationRepository(databasePool ?? requireDatabase());
}
