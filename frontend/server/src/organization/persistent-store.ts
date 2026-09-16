import { randomUUID } from "node:crypto";
import type { Pool, PoolClient, QueryResultRow } from "pg";
import type { ApplicationSession } from "../auth/session.js";
import { can } from "./authorization.js";
import type {
  ApplicationUser,
  AuthContext,
  Department,
  Division,
  Organization,
  OrganizationMembership,
  OrganizationalAssignment,
  OrganizationRole,
  Team,
} from "./types.js";
import type { Permission } from "./permissions.js";

const timestamp = () => new Date().toISOString();
const bootstrapSubject = () => process.env.ORGANIZATION_BOOTSTRAP_SUBJECT?.trim() || null;

class DatabaseHierarchyError extends Error {
  constructor(message: string, public readonly status: 400 | 403 | 404 | 409 | 500) {
    super(message);
    this.name = "DatabaseHierarchyError";
  }
}

type Row = QueryResultRow & Record<string, unknown>;

export class PostgresOrganizationStore {
  constructor(private readonly pool: Pool) {}

  async contextFor(session: ApplicationSession): Promise<AuthContext> {
    const result = await this.pool.query<Row>(`
      SELECT u.id AS user_id, m.organization_id, m.role,
             a.division_id, a.department_id, a.team_id, a.manager_user_id,
             COALESCE(array_agg(p.code) FILTER (WHERE p.code IS NOT NULL), '{}') AS permissions
      FROM users u
      JOIN organization_memberships m ON m.user_id = u.id AND m.status = 'ACTIVE'
      LEFT JOIN user_organizational_assignments a
        ON a.user_id = u.id AND a.organization_id = m.organization_id AND a.is_primary = true
      LEFT JOIN roles r ON r.code = m.role
      LEFT JOIN role_permissions rp ON rp.role_id = r.id
      LEFT JOIN permissions p ON p.id = rp.permission_id
      WHERE u.keycloak_subject = $1
      GROUP BY u.id, m.organization_id, m.role, a.division_id, a.department_id, a.team_id, a.manager_user_id, a.is_primary
      ORDER BY a.is_primary DESC NULLS LAST
      LIMIT 1
    `, [session.subject]);
    const row = result.rows[0];
    return {
      sessionId: session.sessionId,
      userId: typeof row?.user_id === "string" ? row.user_id : null,
      keycloakSubject: session.subject,
      organizationId: typeof row?.organization_id === "string" ? row.organization_id : null,
      role: typeof row?.role === "string" ? row.role as OrganizationRole : null,
      divisionId: typeof row?.division_id === "string" ? row.division_id : null,
      departmentId: typeof row?.department_id === "string" ? row.department_id : null,
      teamId: typeof row?.team_id === "string" ? row.team_id : null,
      managerUserId: typeof row?.manager_user_id === "string" ? row.manager_user_id : null,
      permissions: Array.isArray(row?.permissions) ? row.permissions.filter((value): value is string => typeof value === "string") as import("./permissions.js").Permission[] : [],
    };
  }

  private async authorize(session: ApplicationSession, organizationId: string, permission: Permission, resource: Record<string, unknown> = {}) {
    const auth = await this.contextFor(session);
    if (!auth.userId || !can(auth, permission, { organizationId, ...resource } as Parameters<typeof can>[2])) {
      throw new DatabaseHierarchyError("Organization scope or permission denied", 403);
    }
    return auth;
  }

  async createOrganization(session: ApplicationSession, input: { name: string; code: string; type?: string | null }): Promise<Organization> {
    if (bootstrapSubject() !== session.subject) throw new DatabaseHierarchyError("Organization creation requires the configured bootstrap subject", 403);
    const name = this.required(input.name, "name");
    const code = this.required(input.code, "code").toUpperCase();
    const client = await this.pool.connect();
    try {
      await client.query("BEGIN");
      const organizationResult = await client.query<Row>(`
        INSERT INTO organizations (id, name, code, type) VALUES ($1, $2, $3, $4)
        RETURNING id, name, code, type, status, created_at, updated_at
      `, [randomUUID(), name, code, input.type?.trim() || null]);
      const organization = this.organizationRow(this.row(organizationResult.rows, "Organization"));
      const user = await this.upsertUser(client, session);
      await client.query(`
        INSERT INTO organization_memberships (id, user_id, organization_id, role)
        VALUES ($1, $2, $3, 'ORG_ADMIN')
        ON CONFLICT (user_id, organization_id) DO UPDATE SET status = 'ACTIVE', role = 'ORG_ADMIN', left_at = NULL
      `, [randomUUID(), user.id, organization.id]);
      await client.query("COMMIT");
      return organization;
    } catch (error) {
      await client.query("ROLLBACK");
      if ((error as { code?: string }).code === "23505") throw new DatabaseHierarchyError("Organization code already exists", 409);
      throw error;
    } finally {
      client.release();
    }
  }

  async getOrganization(session: ApplicationSession, organizationId: string): Promise<Organization> {
    await this.authorize(session, organizationId, "organization.read");
    const result = await this.pool.query<Row>("SELECT id, name, code, type, status, created_at, updated_at FROM organizations WHERE id = $1", [organizationId]);
    if (!result.rows[0]) throw new DatabaseHierarchyError("Organization not found", 404);
    return this.organizationRow(this.row(result.rows, "Organization"));
  }

  async updateOrganization(session: ApplicationSession, organizationId: string, input: { name?: string | undefined; type?: string | null | undefined; status?: "ACTIVE" | "SUSPENDED" | undefined }): Promise<Organization> {
    await this.authorize(session, organizationId, "organization.update");
    const current = await this.getOrganization(session, organizationId);
    const result = await this.pool.query<Row>(`
      UPDATE organizations SET name = $2, type = $3, status = $4, updated_at = now()
      WHERE id = $1 RETURNING id, name, code, type, status, created_at, updated_at
    `, [organizationId, input.name === undefined ? current.name : this.required(input.name, "name"), input.type === undefined ? current.type : input.type, input.status ?? current.status]);
    return this.organizationRow(this.row(result.rows, "Organization"));
  }

  async listMembers(session: ApplicationSession, organizationId: string) {
    const auth = await this.contextFor(session);
    if (!auth.userId || !auth.role) throw new DatabaseHierarchyError("Organization access denied", 403);
    const result = await this.pool.query<Row>(`
      SELECT m.id AS membership_id, m.user_id, m.organization_id, m.role, m.status, m.joined_at, m.left_at,
             u.keycloak_subject, u.email, u.username, u.display_name, u.status AS user_status,
             a.id AS assignment_id, a.division_id, a.department_id, a.team_id, a.manager_user_id,
             a.is_primary, a.valid_from, a.valid_until, a.created_at AS assignment_created_at
      FROM organization_memberships m
      JOIN users u ON u.id = m.user_id
      LEFT JOIN user_organizational_assignments a
        ON a.user_id = m.user_id AND a.organization_id = m.organization_id AND a.is_primary = true
      WHERE m.organization_id = $1
      ORDER BY u.display_name NULLS LAST, u.email NULLS LAST
    `, [organizationId]);
    return result.rows.filter((row) => can(auth, "organization.members.read", {
      organizationId,
      divisionId: this.stringOrNull(row.division_id),
      departmentId: this.stringOrNull(row.department_id),
      teamId: this.stringOrNull(row.team_id),
      ownerUserId: this.stringOrNull(row.user_id),
    })).map((row) => ({
      id: row.membership_id,
      userId: row.user_id,
      organizationId: row.organization_id,
      role: row.role,
      status: row.status,
      joinedAt: row.joined_at,
      leftAt: row.left_at,
      user: {
        id: row.user_id,
        keycloakSubject: row.keycloak_subject,
        email: row.email,
        username: row.username,
        displayName: row.display_name,
        status: row.user_status,
      },
      assignment: row.assignment_id ? {
        id: row.assignment_id,
        userId: row.user_id,
        organizationId,
        divisionId: row.division_id,
        departmentId: row.department_id,
        teamId: row.team_id,
        managerUserId: row.manager_user_id,
        isPrimary: row.is_primary,
        validFrom: row.valid_from,
        validUntil: row.valid_until,
        createdAt: row.assignment_created_at,
      } : undefined,
    }));
  }

  async addMember(session: ApplicationSession, organizationId: string, input: { keycloakSubject: string; email?: string | null; username?: string | null; displayName?: string | null; role?: OrganizationRole }) {
    await this.authorize(session, organizationId, "organization.members.manage");
    const client = await this.pool.connect();
    try {
      await client.query("BEGIN");
      const user = await this.upsertUser(client, {
        subject: this.required(input.keycloakSubject, "keycloakSubject"),
        email: input.email ?? null,
        username: input.username ?? null,
        displayName: input.displayName ?? null,
      });
      const role = input.role ?? "EMPLOYEE";
      const existing = await client.query<Row>("SELECT id, user_id, organization_id, role, status, joined_at, left_at FROM organization_memberships WHERE user_id = $1 AND organization_id = $2", [user.id, organizationId]);
      if (existing.rows[0]?.status === "ACTIVE") throw new DatabaseHierarchyError("User is already a member", 409);
      const membership = existing.rows[0]
        ? this.row((await client.query<Row>("UPDATE organization_memberships SET role = $3, status = 'ACTIVE', left_at = NULL WHERE id = $1 RETURNING id, user_id, organization_id, role, status, joined_at, left_at", [existing.rows[0].id, user.id, role])).rows, "Membership")
        : this.row((await client.query<Row>("INSERT INTO organization_memberships (id, user_id, organization_id, role) VALUES ($1, $2, $3, $4) RETURNING id, user_id, organization_id, role, status, joined_at, left_at", [randomUUID(), user.id, organizationId, role])).rows, "Membership");
      await client.query("COMMIT");
      return { membership: this.membershipRow(membership), user };
    } catch (error) {
      await client.query("ROLLBACK");
      client.release();
      throw error;
    }
  }

  async updateMember(session: ApplicationSession, organizationId: string, userId: string, input: { role?: OrganizationRole | undefined; status?: "ACTIVE" | "SUSPENDED" | undefined }) {
    await this.authorize(session, organizationId, "organization.members.manage");
    const result = await this.pool.query<Row>(`
      UPDATE organization_memberships SET role = COALESCE($3, role), status = COALESCE($4, status),
        left_at = CASE WHEN COALESCE($4, status) <> 'ACTIVE' THEN now() ELSE NULL END
      WHERE organization_id = $1 AND user_id = $2
      RETURNING id, user_id, organization_id, role, status, joined_at, left_at
    `, [organizationId, userId, input.role ?? null, input.status ?? null]);
    if (!result.rows[0]) throw new DatabaseHierarchyError("User is not an active organization member", 404);
    const user = await this.pool.query<Row>("SELECT id, keycloak_subject, email, username, display_name, status, created_at, updated_at FROM users WHERE id = $1", [userId]);
    return { membership: this.membershipRow(this.row(result.rows, "Membership")), user: this.userRow(this.row(user.rows, "User")) };
  }

  async removeMember(session: ApplicationSession, organizationId: string, userId: string): Promise<void> {
    await this.authorize(session, organizationId, "organization.members.manage");
    const result = await this.pool.query("UPDATE organization_memberships SET status = 'LEFT', left_at = now() WHERE organization_id = $1 AND user_id = $2 AND status = 'ACTIVE'", [organizationId, userId]);
    if (result.rowCount === 0) throw new DatabaseHierarchyError("User is not an active organization member", 404);
  }

  async createDivision(session: ApplicationSession, organizationId: string, input: { name: string; code: string }): Promise<Division> {
    await this.authorize(session, organizationId, "division.manage");
    const row = await this.insert("INSERT INTO divisions (id, organization_id, name, code) VALUES ($1, $2, $3, $4) RETURNING id, organization_id, name, code, created_at, updated_at", [randomUUID(), organizationId, this.required(input.name, "name"), this.required(input.code, "code").toUpperCase()]);
    return this.divisionRow(row);
  }

  async getDivision(session: ApplicationSession, divisionId: string): Promise<Division> {
    const row = await this.one("SELECT id, organization_id, name, code, created_at, updated_at FROM divisions WHERE id = $1", [divisionId], "Division");
    await this.authorize(session, this.string(row.organization_id), "division.read", { divisionId });
    return this.divisionRow(row);
  }

  async createDepartment(session: ApplicationSession, divisionId: string, input: { name: string; code: string }): Promise<Department> {
    const division = await this.one("SELECT id, organization_id FROM divisions WHERE id = $1", [divisionId], "Division");
    await this.authorize(session, this.string(division.organization_id), "department.manage", { divisionId });
    return this.departmentRow(await this.insert("INSERT INTO departments (id, division_id, name, code) VALUES ($1, $2, $3, $4) RETURNING id, division_id, name, code, created_at, updated_at", [randomUUID(), divisionId, this.required(input.name, "name"), this.required(input.code, "code").toUpperCase()]));
  }

  async getDepartment(session: ApplicationSession, departmentId: string): Promise<Department> {
    const row = await this.one("SELECT d.id, d.division_id, d.name, d.code, d.created_at, d.updated_at, v.organization_id FROM departments d JOIN divisions v ON v.id = d.division_id WHERE d.id = $1", [departmentId], "Department");
    await this.authorize(session, this.string(row.organization_id), "department.read", { divisionId: this.string(row.division_id), departmentId });
    return this.departmentRow(row);
  }

  async createTeam(session: ApplicationSession, departmentId: string, input: { name: string; code: string }): Promise<Team> {
    const parent = await this.one("SELECT d.id, d.division_id, v.organization_id FROM departments d JOIN divisions v ON v.id = d.division_id WHERE d.id = $1", [departmentId], "Department");
    await this.authorize(session, this.string(parent.organization_id), "team.manage", { divisionId: this.string(parent.division_id), departmentId });
    return this.teamRow(await this.insert("INSERT INTO teams (id, department_id, name, code) VALUES ($1, $2, $3, $4) RETURNING id, department_id, name, code, created_at, updated_at", [randomUUID(), departmentId, this.required(input.name, "name"), this.required(input.code, "code").toUpperCase()]));
  }

  async getTeam(session: ApplicationSession, teamId: string): Promise<Team> {
    const row = await this.one("SELECT t.id, t.department_id, t.name, t.code, t.created_at, t.updated_at, d.division_id, v.organization_id FROM teams t JOIN departments d ON d.id = t.department_id JOIN divisions v ON v.id = d.division_id WHERE t.id = $1", [teamId], "Team");
    await this.authorize(session, this.string(row.organization_id), "team.read", { divisionId: this.string(row.division_id), departmentId: this.string(row.department_id), teamId });
    return this.teamRow(row);
  }

  async updateAssignment(session: ApplicationSession, userId: string, input: { organizationId: string; divisionId?: string | null | undefined; departmentId?: string | null | undefined; teamId?: string | null | undefined; managerUserId?: string | null | undefined; isPrimary?: boolean | undefined }): Promise<OrganizationalAssignment> {
    await this.authorize(session, input.organizationId, "organization.members.manage");
    await this.one("SELECT id FROM organization_memberships WHERE user_id = $1 AND organization_id = $2 AND status = 'ACTIVE'", [userId, input.organizationId], "Active membership");
    if (input.divisionId) await this.one("SELECT id FROM divisions WHERE id = $1 AND organization_id = $2", [input.divisionId, input.organizationId], "Division");
    if (input.departmentId) await this.one("SELECT d.id FROM departments d JOIN divisions v ON v.id = d.division_id WHERE d.id = $1 AND v.id = $2", [input.departmentId, input.divisionId], "Department");
    if (input.teamId) await this.one("SELECT t.id FROM teams t JOIN departments d ON d.id = t.department_id WHERE t.id = $1 AND d.id = $2", [input.teamId, input.departmentId], "Team");
    if (input.managerUserId) await this.one("SELECT id FROM organization_memberships WHERE user_id = $1 AND organization_id = $2 AND status = 'ACTIVE'", [input.managerUserId, input.organizationId], "Manager membership");
    const row = await this.insert(`
      INSERT INTO user_organizational_assignments (id, user_id, organization_id, division_id, department_id, team_id, manager_user_id, is_primary)
      VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
      ON CONFLICT (user_id, organization_id, is_primary) DO UPDATE SET division_id = EXCLUDED.division_id, department_id = EXCLUDED.department_id, team_id = EXCLUDED.team_id, manager_user_id = EXCLUDED.manager_user_id
      RETURNING id, user_id, organization_id, division_id, department_id, team_id, manager_user_id, is_primary, valid_from, valid_until, created_at
    `, [randomUUID(), userId, input.organizationId, input.divisionId ?? null, input.departmentId ?? null, input.teamId ?? null, input.managerUserId ?? null, input.isPrimary ?? true]);
    return this.assignmentRow(row);
  }

  private async upsertUser(client: PoolClient, identity: Pick<ApplicationSession, "subject" | "email" | "username" | "displayName">): Promise<ApplicationUser> {
    const row = this.row((await client.query<Row>(`
      INSERT INTO users (id, keycloak_subject, email, username, display_name, last_login_at)
      VALUES ($1, $2, $3, $4, $5, now())
      ON CONFLICT (keycloak_subject) DO UPDATE SET email = EXCLUDED.email, username = EXCLUDED.username, display_name = EXCLUDED.display_name, last_login_at = now()
      RETURNING id, keycloak_subject, email, username, display_name, status, created_at, updated_at
    `, [randomUUID(), identity.subject, identity.email, identity.username, identity.displayName])).rows, "User");
    return this.userRow(row);
  }

  private async insert(sql: string, values: unknown[]): Promise<Row> {
    try {
      return this.row((await this.pool.query<Row>(sql, values)).rows, "Database record");
    } catch (error) {
      if ((error as { code?: string }).code === "23505") throw new DatabaseHierarchyError("A resource with that code already exists", 409);
      throw error;
    }
  }

  private async one(sql: string, values: unknown[], label: string): Promise<Row> {
    const result = await this.pool.query<Row>(sql, values);
    if (!result.rows[0]) throw new DatabaseHierarchyError(`${label} not found`, 404);
    return result.rows[0];
  }

  private row(rows: Row[], label: string): Row {
    if (!rows[0]) throw new DatabaseHierarchyError(`${label} was not created`, 500);
    return rows[0];
  }

  private required(value: string | undefined, field: string): string {
    const normalized = value?.trim();
    if (!normalized) throw new DatabaseHierarchyError(`${field} is required`, 400);
    return normalized;
  }

  private string(value: unknown): string {
    if (value instanceof Date) return value.toISOString();
    if (typeof value === "string") return value;
    throw new DatabaseHierarchyError("Invalid database relationship", 409);
  }

  private stringOrNull(value: unknown): string | null {
    return typeof value === "string" ? value : null;
  }

  private organizationRow(row: Row): Organization {
    return { id: this.string(row.id), name: this.string(row.name), code: this.string(row.code), type: this.stringOrNull(row.type), status: this.string(row.status) as Organization["status"], createdAt: this.string(row.created_at), updatedAt: this.string(row.updated_at) };
  }

  private divisionRow(row: Row): Division {
    return { id: this.string(row.id), organizationId: this.string(row.organization_id), name: this.string(row.name), code: this.string(row.code), createdAt: this.string(row.created_at), updatedAt: this.string(row.updated_at) };
  }

  private departmentRow(row: Row): Department {
    return { id: this.string(row.id), divisionId: this.string(row.division_id), name: this.string(row.name), code: this.string(row.code), createdAt: this.string(row.created_at), updatedAt: this.string(row.updated_at) };
  }

  private teamRow(row: Row): Team {
    return { id: this.string(row.id), departmentId: this.string(row.department_id), name: this.string(row.name), code: this.string(row.code), createdAt: this.string(row.created_at), updatedAt: this.string(row.updated_at) };
  }

  private userRow(row: Row): ApplicationUser {
    return { id: this.string(row.id), keycloakSubject: this.string(row.keycloak_subject), email: this.stringOrNull(row.email), username: this.stringOrNull(row.username), displayName: this.stringOrNull(row.display_name), status: this.string(row.status) as ApplicationUser["status"], createdAt: this.string(row.created_at), updatedAt: this.string(row.updated_at) };
  }

  private membershipRow(row: Row): OrganizationMembership {
    return { id: this.string(row.id), userId: this.string(row.user_id), organizationId: this.string(row.organization_id), role: this.string(row.role) as OrganizationRole, status: this.string(row.status) as OrganizationMembership["status"], joinedAt: this.string(row.joined_at), leftAt: this.stringOrNull(row.left_at) };
  }

  private assignmentRow(row: Row): OrganizationalAssignment {
    return { id: this.string(row.id), userId: this.string(row.user_id), organizationId: this.string(row.organization_id), divisionId: this.stringOrNull(row.division_id), departmentId: this.stringOrNull(row.department_id), teamId: this.stringOrNull(row.team_id), managerUserId: this.stringOrNull(row.manager_user_id), isPrimary: Boolean(row.is_primary), validFrom: this.string(row.valid_from), validUntil: this.stringOrNull(row.valid_until), createdAt: this.string(row.created_at) };
  }
}
