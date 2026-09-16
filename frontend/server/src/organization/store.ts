import { randomUUID } from "node:crypto";
import type { ApplicationSession } from "../auth/session.js";
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
import { permissionsForRole, type Permission } from "./permissions.js";
import { can } from "./authorization.js";
import { databaseConfigured, databasePool } from "../database/pool.js";
import { PostgresOrganizationStore } from "./persistent-store.js";

const now = () => new Date().toISOString();
const bootstrapSubject = () => process.env.ORGANIZATION_BOOTSTRAP_SUBJECT?.trim() || null;

export class HierarchyError extends Error {
  constructor(
    message: string,
    public readonly status: 400 | 403 | 404 | 409,
  ) {
    super(message);
    this.name = "HierarchyError";
  }
}

export class OrganizationStore {
  private readonly organizations = new Map<string, Organization>();
  private readonly divisions = new Map<string, Division>();
  private readonly departments = new Map<string, Department>();
  private readonly teams = new Map<string, Team>();
  private readonly users = new Map<string, ApplicationUser>();
  private readonly usersBySubject = new Map<string, string>();
  private readonly memberships = new Map<string, OrganizationMembership>();
  private readonly assignments = new Map<string, OrganizationalAssignment>();

  contextFor(session: ApplicationSession): AuthContext {
    const userId = this.usersBySubject.get(session.subject) ?? null;
    const membership = userId
      ? [...this.memberships.values()].find(
          (candidate) => candidate.userId === userId && candidate.status === "ACTIVE",
        )
      : undefined;
    const assignment = membership && userId
      ? [...this.assignments.values()].find(
          (candidate) => candidate.userId === userId && candidate.organizationId === membership.organizationId && candidate.isPrimary,
        )
      : undefined;
    return {
      sessionId: session.sessionId,
      userId,
      keycloakSubject: session.subject,
      organizationId: membership?.organizationId ?? null,
      role: membership?.role ?? null,
      divisionId: assignment?.divisionId ?? null,
      departmentId: assignment?.departmentId ?? null,
      teamId: assignment?.teamId ?? null,
      managerUserId: assignment?.managerUserId ?? null,
      permissions: membership?.role ? permissionsForRole(membership.role) : [],
    };
  }

  canBootstrap(session: ApplicationSession): boolean {
    return bootstrapSubject() === session.subject;
  }

  createOrganization(
    session: ApplicationSession,
    input: { name: string; code: string; type?: string | null },
  ): Organization {
    if (!this.canBootstrap(session)) {
      throw new HierarchyError("Organization creation requires the configured bootstrap subject", 403);
    }
    const name = this.requiredText(input.name, "name");
    const code = this.requiredText(input.code, "code").toUpperCase();
    if ([...this.organizations.values()].some((organization) => organization.code === code)) {
      throw new HierarchyError("Organization code already exists", 409);
    }
    const organization: Organization = {
      id: randomUUID(),
      name,
      code,
      type: input.type?.trim() || null,
      status: "ACTIVE",
      createdAt: now(),
      updatedAt: now(),
    };
    this.organizations.set(organization.id, organization);
    if (this.canBootstrap(session)) {
      const user = this.upsertUser(session, organization.id);
      this.addMembership(user.id, organization.id, "ORG_ADMIN");
    }
    return organization;
  }

  getOrganization(session: ApplicationSession, organizationId: string): Organization {
    this.requirePermission(session, organizationId, "organization.read");
    return this.organization(organizationId);
  }

  updateOrganization(
    session: ApplicationSession,
    organizationId: string,
    input: { name?: string | undefined; type?: string | null | undefined; status?: "ACTIVE" | "SUSPENDED" | undefined },
  ): Organization {
    this.requirePermission(session, organizationId, "organization.update");
    const organization = this.organization(organizationId);
    if (input.name !== undefined) organization.name = this.requiredText(input.name, "name");
    if (input.type !== undefined) organization.type = input.type?.trim() || null;
    if (input.status !== undefined) organization.status = input.status;
    organization.updatedAt = now();
    return organization;
  }

  listMembers(session: ApplicationSession, organizationId: string) {
    const context = this.contextFor(session);
    if (!context.userId || !context.role) throw new HierarchyError("Organization access denied", 403);
    return [...this.memberships.values()]
      .filter((membership) => membership.organizationId === organizationId)
      .filter((membership) => {
        const assignment = [...this.assignments.values()].find(
          (candidate) => candidate.userId === membership.userId && candidate.organizationId === organizationId && candidate.isPrimary,
        );
        return can(context, "organization.members.read", {
          organizationId,
          divisionId: assignment?.divisionId,
          departmentId: assignment?.departmentId,
          teamId: assignment?.teamId,
          ownerUserId: membership.userId,
        });
      })
      .map((membership) => ({
        ...membership,
        user: this.users.get(membership.userId),
        assignment: [...this.assignments.values()].find(
          (assignment) => assignment.userId === membership.userId && assignment.organizationId === organizationId,
        ),
      }));
  }

  addMember(
    session: ApplicationSession,
    organizationId: string,
    input: {
      keycloakSubject: string;
      email?: string | null;
      username?: string | null;
      displayName?: string | null;
      role?: OrganizationRole;
    },
  ) {
    this.requirePermission(session, organizationId, "organization.members.manage");
    const subject = this.requiredText(input.keycloakSubject, "keycloakSubject");
    const role = input.role ?? "EMPLOYEE";
    const user = this.upsertUser(
      {
        subject,
        email: input.email ?? null,
        username: input.username ?? null,
        displayName: input.displayName ?? null,
      },
      organizationId,
    );
    const existing = [...this.memberships.values()].find(
      (membership) => membership.userId === user.id && membership.organizationId === organizationId,
    );
    if (existing && existing.status === "ACTIVE") throw new HierarchyError("User is already a member", 409);
    const membership = existing ?? this.addMembership(user.id, organizationId, role);
    if (existing) {
      existing.status = "ACTIVE";
      existing.role = role;
      existing.leftAt = null;
    }
    return { membership, user };
  }

  updateMember(
    session: ApplicationSession,
    organizationId: string,
    userId: string,
    input: { role?: OrganizationRole | undefined; status?: "ACTIVE" | "SUSPENDED" | undefined },
  ) {
    this.requirePermission(session, organizationId, "organization.members.manage");
    const membership = this.membership(userId, organizationId);
    if (input.role !== undefined) membership.role = input.role;
    if (input.status !== undefined) membership.status = input.status;
    if (membership.status !== "ACTIVE") membership.leftAt = now();
    return { membership, user: this.users.get(userId) };
  }

  removeMember(session: ApplicationSession, organizationId: string, userId: string): void {
    this.requirePermission(session, organizationId, "organization.members.manage");
    const membership = this.membership(userId, organizationId);
    membership.status = "LEFT";
    membership.leftAt = now();
  }

  createDivision(session: ApplicationSession, organizationId: string, input: { name: string; code: string }): Division {
    this.requirePermission(session, organizationId, "division.manage");
    this.organization(organizationId);
    return this.createUnique(this.divisions, {
      id: randomUUID(),
      organizationId,
      name: this.requiredText(input.name, "name"),
      code: this.requiredText(input.code, "code").toUpperCase(),
      createdAt: now(),
      updatedAt: now(),
    }, (value) => value.organizationId === organizationId && value.code === input.code.toUpperCase());
  }

  getDivision(session: ApplicationSession, divisionId: string): Division {
    const division = this.division(divisionId);
    this.requirePermission(session, division.organizationId, "division.read", { divisionId: division.id });
    return division;
  }

  createDepartment(session: ApplicationSession, divisionId: string, input: { name: string; code: string }): Department {
    const division = this.division(divisionId);
    this.requirePermission(session, division.organizationId, "department.manage", { divisionId: division.id });
    return this.createUnique(this.departments, {
      id: randomUUID(),
      divisionId,
      name: this.requiredText(input.name, "name"),
      code: this.requiredText(input.code, "code").toUpperCase(),
      createdAt: now(),
      updatedAt: now(),
    }, (value) => value.divisionId === divisionId && value.code === input.code.toUpperCase());
  }

  getDepartment(session: ApplicationSession, departmentId: string): Department {
    const department = this.department(departmentId);
    const division = this.division(department.divisionId);
    this.requirePermission(session, division.organizationId, "department.read", {
      divisionId: division.id,
      departmentId: department.id,
    });
    return department;
  }

  createTeam(session: ApplicationSession, departmentId: string, input: { name: string; code: string }): Team {
    const department = this.department(departmentId);
    const division = this.division(department.divisionId);
    this.requirePermission(session, division.organizationId, "team.manage", {
      divisionId: division.id,
      departmentId: department.id,
    });
    return this.createUnique(this.teams, {
      id: randomUUID(),
      departmentId,
      name: this.requiredText(input.name, "name"),
      code: this.requiredText(input.code, "code").toUpperCase(),
      createdAt: now(),
      updatedAt: now(),
    }, (value) => value.departmentId === departmentId && value.code === input.code.toUpperCase());
  }

  getTeam(session: ApplicationSession, teamId: string): Team {
    const team = this.team(teamId);
    const department = this.department(team.departmentId);
    const division = this.division(department.divisionId);
    this.requirePermission(session, division.organizationId, "team.read", {
      divisionId: division.id,
      departmentId: department.id,
      teamId: team.id,
    });
    return team;
  }

  updateAssignment(
    session: ApplicationSession,
    userId: string,
    input: {
      organizationId: string;
      divisionId?: string | null | undefined;
      departmentId?: string | null | undefined;
      teamId?: string | null | undefined;
      managerUserId?: string | null | undefined;
      isPrimary?: boolean | undefined;
    },
  ): OrganizationalAssignment {
    this.requirePermission(session, input.organizationId, "organization.members.manage");
    this.organization(input.organizationId);
    this.membership(userId, input.organizationId);
    const division = input.divisionId ? this.division(input.divisionId) : null;
    const department = input.departmentId ? this.department(input.departmentId) : null;
    const team = input.teamId ? this.team(input.teamId) : null;
    if (division && division.organizationId !== input.organizationId) throw new HierarchyError("Division is outside organization", 409);
    if (department && (!division || department.divisionId !== division.id)) throw new HierarchyError("Department must belong to the selected division", 409);
    if (team && (!department || team.departmentId !== department.id)) throw new HierarchyError("Team must belong to the selected department", 409);
    if (input.managerUserId) this.membership(input.managerUserId, input.organizationId);
    const existing = [...this.assignments.values()].find(
      (assignment) => assignment.userId === userId && assignment.organizationId === input.organizationId,
    );
    const assignment: OrganizationalAssignment = existing ?? {
      id: randomUUID(),
      userId,
      organizationId: input.organizationId,
      divisionId: null,
      departmentId: null,
      teamId: null,
      managerUserId: null,
      isPrimary: input.isPrimary ?? true,
      validFrom: now(),
      validUntil: null,
      createdAt: now(),
    };
    assignment.divisionId = input.divisionId ?? null;
    assignment.departmentId = input.departmentId ?? null;
    assignment.teamId = input.teamId ?? null;
    assignment.managerUserId = input.managerUserId ?? null;
    assignment.isPrimary = input.isPrimary ?? assignment.isPrimary;
    this.assignments.set(assignment.id, assignment);
    return assignment;
  }

  private upsertUser(
    identity: Pick<ApplicationSession, "subject" | "email" | "username" | "displayName">,
    _organizationId: string,
  ): ApplicationUser {
    const existingId = this.usersBySubject.get(identity.subject);
    if (existingId) {
      const existing = this.users.get(existingId);
      if (existing) return existing;
    }
    const timestamp = now();
    const user: ApplicationUser = {
      id: randomUUID(),
      keycloakSubject: identity.subject,
      email: identity.email,
      username: identity.username,
      displayName: identity.displayName,
      status: "ACTIVE",
      createdAt: timestamp,
      updatedAt: timestamp,
    };
    this.users.set(user.id, user);
    this.usersBySubject.set(user.keycloakSubject, user.id);
    return user;
  }

  private addMembership(userId: string, organizationId: string, role: OrganizationRole): OrganizationMembership {
    const membership: OrganizationMembership = {
      id: randomUUID(),
      userId,
      organizationId,
      role,
      status: "ACTIVE",
      joinedAt: now(),
      leftAt: null,
    };
    this.memberships.set(membership.id, membership);
    return membership;
  }

  private requirePermission(
    session: ApplicationSession,
    organizationId: string,
    permission: Permission,
    resource: Omit<import("./authorization.js").ResourceContext, "organizationId"> = {},
  ): void {
    const context = this.contextFor(session);
    if (!context.userId || !can(context, permission, { organizationId, ...resource })) {
      throw new HierarchyError("Organization scope or permission denied", 403);
    }
  }

  private membership(userId: string, organizationId: string): OrganizationMembership {
    const membership = [...this.memberships.values()].find(
      (candidate) => candidate.userId === userId && candidate.organizationId === organizationId && candidate.status === "ACTIVE",
    );
    if (!membership) throw new HierarchyError("User is not an active organization member", 404);
    return membership;
  }

  private organization(id: string): Organization {
    const value = this.organizations.get(id);
    if (!value) throw new HierarchyError("Organization not found", 404);
    return value;
  }

  private division(id: string): Division {
    const value = this.divisions.get(id);
    if (!value) throw new HierarchyError("Division not found", 404);
    return value;
  }

  private department(id: string): Department {
    const value = this.departments.get(id);
    if (!value) throw new HierarchyError("Department not found", 404);
    return value;
  }

  private team(id: string): Team {
    const value = this.teams.get(id);
    if (!value) throw new HierarchyError("Team not found", 404);
    return value;
  }

  private requiredText(value: string | undefined, field: string): string {
    const normalized = value?.trim();
    if (!normalized) throw new HierarchyError(`${field} is required`, 400);
    return normalized;
  }

  private createUnique<T extends { id: string }>(map: Map<string, T>, value: T, duplicate: (candidate: T) => boolean): T {
    if ([...map.values()].some(duplicate)) throw new HierarchyError("A resource with that code already exists", 409);
    map.set(value.id, value);
    return value;
  }
}

const memoryStoreRequested = process.env.ORG_STORE_MODE === "memory" || process.env.NODE_ENV === "test";

if (!databaseConfigured && !memoryStoreRequested) {
  throw new Error("DATABASE_URL is required for the organization hierarchy; set ORG_STORE_MODE=memory only for tests");
}

export const organizationStore = databaseConfigured && databasePool
  ? new PostgresOrganizationStore(databasePool)
  : new OrganizationStore();
