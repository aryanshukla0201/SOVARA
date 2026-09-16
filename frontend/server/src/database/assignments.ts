import { randomUUID } from "node:crypto";
import type { Pool, PoolClient, QueryResultRow } from "pg";
import { databasePool, requireDatabase } from "./pool.js";
import type { OrganizationalAssignmentRecord, UserRecord } from "./models.js";

export type AssignmentInput = {
  userId: string;
  organizationId: string;
  divisionId?: string | null;
  departmentId?: string | null;
  teamId?: string | null;
  managerUserId?: string | null;
  isPrimary?: boolean;
  validFrom?: Date | string;
  validUntil?: Date | string | null;
};

type AssignmentRow = QueryResultRow & {
  id: string;
  user_id: string;
  organization_id: string;
  division_id: string | null;
  department_id: string | null;
  team_id: string | null;
  manager_user_id: string | null;
  is_primary: boolean;
  valid_from: Date;
  valid_until: Date | null;
  created_at: Date;
};

function required(value: string, field: string): string {
  const normalized = value.trim();
  if (!normalized) throw new Error(`${field} is required`);
  return normalized;
}

function assignmentFromRow(row: AssignmentRow): OrganizationalAssignmentRecord {
  return {
    id: row.id,
    userId: row.user_id,
    organizationId: row.organization_id,
    divisionId: row.division_id,
    departmentId: row.department_id,
    teamId: row.team_id,
    managerUserId: row.manager_user_id,
    isPrimary: row.is_primary,
    validFrom: row.valid_from,
    validUntil: row.valid_until,
    createdAt: row.created_at,
  };
}

const assignmentColumns = `id, user_id, organization_id, division_id, department_id,
  team_id, manager_user_id, is_primary, valid_from, valid_until, created_at`;

const userColumns = `u.id, u.keycloak_subject, u.email, u.username, u.display_name,
  u.status, u.created_at, u.updated_at, u.last_login_at`;

type UserRow = QueryResultRow & {
  id: string;
  keycloak_subject: string;
  email: string | null;
  username: string | null;
  display_name: string | null;
  status: UserRecord["status"];
  created_at: Date;
  updated_at: Date;
  last_login_at: Date | null;
};

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

export class AssignmentRepository {
  constructor(private readonly pool: Pool = requireDatabase()) {}

  async create(input: AssignmentInput): Promise<OrganizationalAssignmentRecord> {
    const userId = required(input.userId, "userId");
    const organizationId = required(input.organizationId, "organizationId");
    if (input.managerUserId === userId) throw new Error("managerUserId cannot equal userId");

    const client = await this.pool.connect();
    try {
      await client.query("BEGIN");
      if (input.managerUserId) {
        const managerUserId = required(input.managerUserId, "managerUserId");
        const cycle = await client.query(
          `WITH RECURSIVE manager_chain(user_id, manager_user_id) AS (
             SELECT user_id, manager_user_id
             FROM user_organizational_assignments
             WHERE user_id = $1 AND organization_id = $2 AND is_primary = true
             UNION ALL
             SELECT assignment.user_id, assignment.manager_user_id
             FROM user_organizational_assignments assignment
             JOIN manager_chain chain ON assignment.user_id = chain.manager_user_id
             WHERE assignment.organization_id = $2 AND assignment.is_primary = true
           )
           SELECT 1 FROM manager_chain
           WHERE user_id = $3 OR manager_user_id = $3
           LIMIT 1`,
          [managerUserId, organizationId, userId],
        );
        if (cycle.rowCount) throw new Error("Manager relationship would create a reporting cycle");
      }
      if (input.isPrimary !== false) {
        await client.query(
          `UPDATE user_organizational_assignments
           SET is_primary = false, valid_until = COALESCE(valid_until, now())
           WHERE user_id = $1 AND organization_id = $2 AND is_primary = true`,
          [userId, organizationId],
        );
      }
      const result = await client.query<AssignmentRow>(
        `INSERT INTO user_organizational_assignments
           (id, user_id, organization_id, division_id, department_id, team_id,
            manager_user_id, is_primary, valid_from, valid_until)
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8, COALESCE($9, now()), $10)
         RETURNING ${assignmentColumns}`,
        [
          randomUUID(),
          userId,
          organizationId,
          input.divisionId ?? null,
          input.departmentId ?? null,
          input.teamId ?? null,
          input.managerUserId ?? null,
          input.isPrimary !== false,
          input.validFrom ?? null,
          input.validUntil ?? null,
        ],
      );
      const row = result.rows[0];
      if (!row) throw new Error("Assignment insert returned no row");
      await client.query("COMMIT");
      return assignmentFromRow(row);
    } catch (error) {
      await client.query("ROLLBACK");
      throw error;
    } finally {
      client.release();
    }
  }

  async findPrimary(userId: string, organizationId: string): Promise<OrganizationalAssignmentRecord | null> {
    const result = await this.pool.query<AssignmentRow>(
      `SELECT ${assignmentColumns}
       FROM user_organizational_assignments
       WHERE user_id = $1 AND organization_id = $2 AND is_primary = true`,
      [required(userId, "userId"), required(organizationId, "organizationId")],
    );
    return result.rows[0] ? assignmentFromRow(result.rows[0]) : null;
  }

  async listHistory(userId: string, organizationId: string): Promise<OrganizationalAssignmentRecord[]> {
    const result = await this.pool.query<AssignmentRow>(
      `SELECT ${assignmentColumns}
       FROM user_organizational_assignments
       WHERE user_id = $1 AND organization_id = $2
       ORDER BY valid_from DESC`,
      [required(userId, "userId"), required(organizationId, "organizationId")],
    );
    return result.rows.map(assignmentFromRow);
  }

  async listReports(managerUserId: string, organizationId: string): Promise<OrganizationalAssignmentRecord[]> {
    const result = await this.pool.query<AssignmentRow>(
      `SELECT ${assignmentColumns}
       FROM user_organizational_assignments
       WHERE manager_user_id = $1 AND organization_id = $2 AND valid_until IS NULL
       ORDER BY user_id ASC`,
      [required(managerUserId, "managerUserId"), required(organizationId, "organizationId")],
    );
    return result.rows.map(assignmentFromRow);
  }

  async findManager(userId: string, organizationId: string): Promise<UserRecord | null> {
    const result = await this.pool.query<UserRow>(
      `SELECT ${userColumns}
       FROM users u
       JOIN user_organizational_assignments assignment
         ON assignment.manager_user_id = u.id
        AND assignment.organization_id = $2
        AND assignment.user_id = $1
        AND assignment.is_primary = true
        AND assignment.valid_until IS NULL
       JOIN organization_memberships membership
         ON membership.user_id = u.id
        AND membership.organization_id = $2
        AND membership.status = 'ACTIVE'`,
      [required(userId, "userId"), required(organizationId, "organizationId")],
    );
    return result.rows[0] ? userFromRow(result.rows[0]) : null;
  }

  async listDirectReportUsers(managerUserId: string, organizationId: string): Promise<UserRecord[]> {
    const result = await this.pool.query<UserRow>(
      `SELECT ${userColumns}
       FROM users u
       JOIN user_organizational_assignments assignment
         ON assignment.user_id = u.id
        AND assignment.manager_user_id = $1
        AND assignment.organization_id = $2
        AND assignment.is_primary = true
        AND assignment.valid_until IS NULL
       JOIN organization_memberships membership
         ON membership.user_id = u.id
        AND membership.organization_id = $2
        AND membership.status = 'ACTIVE'
       ORDER BY u.display_name NULLS LAST, u.id`,
      [required(managerUserId, "managerUserId"), required(organizationId, "organizationId")],
    );
    return result.rows.map(userFromRow);
  }

  async listDepartmentUsers(departmentId: string, organizationId: string): Promise<UserRecord[]> {
    return this.listUsersInUnit("department_id", departmentId, organizationId);
  }

  async listTeamUsers(teamId: string, organizationId: string): Promise<UserRecord[]> {
    return this.listUsersInUnit("team_id", teamId, organizationId);
  }

  private async listUsersInUnit(
    column: "department_id" | "team_id",
    unitId: string,
    organizationId: string,
  ): Promise<UserRecord[]> {
    const result = await this.pool.query<UserRow>(
      `SELECT ${userColumns}
       FROM users u
       JOIN user_organizational_assignments assignment
         ON assignment.user_id = u.id
        AND assignment.${column} = $1
        AND assignment.organization_id = $2
        AND assignment.is_primary = true
        AND assignment.valid_until IS NULL
       JOIN organization_memberships membership
         ON membership.user_id = u.id
        AND membership.organization_id = $2
        AND membership.status = 'ACTIVE'
       ORDER BY u.display_name NULLS LAST, u.id`,
      [required(unitId, column), required(organizationId, "organizationId")],
    );
    return result.rows.map(userFromRow);
  }
}

export function assignmentRepository(): AssignmentRepository {
  return new AssignmentRepository(databasePool ?? requireDatabase());
}

export type AssignmentClient = PoolClient;
