import { randomUUID } from "node:crypto";
import type { Pool, QueryResultRow } from "pg";
import { databasePool, requireDatabase } from "./pool.js";
import type { MembershipStatus, OrganizationMembershipRecord } from "./models.js";

export type MembershipInput = {
  userId: string;
  organizationId: string;
  role: string;
};

type MembershipRow = QueryResultRow & {
  id: string;
  user_id: string;
  organization_id: string;
  role: string;
  status: MembershipStatus;
  joined_at: Date;
  left_at: Date | null;
};

function required(value: string, field: string): string {
  const normalized = value.trim();
  if (!normalized) throw new Error(`${field} is required`);
  return normalized;
}

function membershipFromRow(row: MembershipRow): OrganizationMembershipRecord {
  return {
    id: row.id,
    userId: row.user_id,
    organizationId: row.organization_id,
    role: row.role,
    status: row.status,
    joinedAt: row.joined_at,
    leftAt: row.left_at,
  };
}

const membershipColumns = `id, user_id, organization_id, role, status,
  joined_at, left_at`;

export class MembershipRepository {
  constructor(private readonly pool: Pool = requireDatabase()) {}

  async add(input: MembershipInput): Promise<OrganizationMembershipRecord> {
    const result = await this.pool.query<MembershipRow>(
      `INSERT INTO organization_memberships
         (id, user_id, organization_id, role, status, joined_at, left_at)
       VALUES ($1, $2, $3, $4, 'ACTIVE', now(), NULL)
       ON CONFLICT (user_id, organization_id) DO UPDATE SET
         role = EXCLUDED.role,
         status = 'ACTIVE',
         left_at = NULL
       RETURNING ${membershipColumns}`,
      [
        randomUUID(),
        required(input.userId, "userId"),
        required(input.organizationId, "organizationId"),
        required(input.role, "role"),
      ],
    );
    const row = result.rows[0];
    if (!row) throw new Error("Membership insert returned no row");
    return membershipFromRow(row);
  }

  async find(userId: string, organizationId: string): Promise<OrganizationMembershipRecord | null> {
    const result = await this.pool.query<MembershipRow>(
      `SELECT ${membershipColumns}
       FROM organization_memberships
       WHERE user_id = $1 AND organization_id = $2`,
      [required(userId, "userId"), required(organizationId, "organizationId")],
    );
    return result.rows[0] ? membershipFromRow(result.rows[0]) : null;
  }

  async listForUser(userId: string): Promise<OrganizationMembershipRecord[]> {
    const result = await this.pool.query<MembershipRow>(
      `SELECT ${membershipColumns}
       FROM organization_memberships
       WHERE user_id = $1
       ORDER BY joined_at ASC`,
      [required(userId, "userId")],
    );
    return result.rows.map(membershipFromRow);
  }

  async listForOrganization(organizationId: string): Promise<OrganizationMembershipRecord[]> {
    const result = await this.pool.query<MembershipRow>(
      `SELECT ${membershipColumns}
       FROM organization_memberships
       WHERE organization_id = $1
       ORDER BY joined_at ASC`,
      [required(organizationId, "organizationId")],
    );
    return result.rows.map(membershipFromRow);
  }

  async setStatus(
    userId: string,
    organizationId: string,
    status: MembershipStatus,
  ): Promise<OrganizationMembershipRecord | null> {
    const result = await this.pool.query<MembershipRow>(
      `UPDATE organization_memberships
       SET status = $3,
           left_at = CASE WHEN $3 = 'LEFT' THEN COALESCE(left_at, now()) ELSE NULL END
       WHERE user_id = $1 AND organization_id = $2
       RETURNING ${membershipColumns}`,
      [required(userId, "userId"), required(organizationId, "organizationId"), status],
    );
    return result.rows[0] ? membershipFromRow(result.rows[0]) : null;
  }
}

export function membershipRepository(): MembershipRepository {
  return new MembershipRepository(databasePool ?? requireDatabase());
}
