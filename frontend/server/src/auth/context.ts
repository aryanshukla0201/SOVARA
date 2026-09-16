import { databaseConfigured } from "../database/pool.js";
import { rolePermissionIds } from "../database/authorization-data.js";
import { membershipRepository } from "../database/memberships.js";
import { userRepository } from "../database/users.js";
import { assignmentRepository } from "../database/assignments.js";
import { isOrganizationRole, type OrganizationRole } from "../organization/roles.js";
import { permissionsForRole, type Permission } from "../organization/permissions.js";
import type { ApplicationSession } from "./session.js";

// This is the only request context used by backend authorization code.
// It is constructed server-side from the session and application database.
export type AuthContext = {
  sessionId: string;
  userId: string | null;
  keycloakSubject: string;
  email: string | null;
  username: string | null;
  displayName: string | null;
  organizationId: string | null;
  role: OrganizationRole | null;
  roleIds: readonly string[];
  permissions: readonly Permission[];
  permissionIds: readonly string[];
  divisionId: string | null;
  departmentId: string | null;
  teamId: string | null;
  managerUserId: string | null;
};

function baseContext(session: ApplicationSession): AuthContext {
  const role = session.role && isOrganizationRole(session.role) ? session.role : null;
  return {
    sessionId: session.sessionId,
    userId: session.applicationUserId,
    keycloakSubject: session.subject,
    email: session.email,
    username: session.username,
    displayName: session.displayName,
    organizationId: session.organizationId,
    role,
    roleIds: [],
    permissions: role ? permissionsForRole(role) : [],
    permissionIds: [],
    divisionId: null,
    departmentId: null,
    teamId: null,
    managerUserId: null,
  };
}

export async function resolveAuthContext(session: ApplicationSession): Promise<AuthContext> {
  if (!databaseConfigured) return baseContext(session);

  const user = await userRepository().findByKeycloakSubject(session.subject);
  if (!user || user.status !== "ACTIVE") {
    return {
      ...baseContext(session),
      userId: user?.id ?? null,
      organizationId: null,
      role: null,
      roleIds: [],
      permissions: [],
      permissionIds: [],
    };
  }

  const membership = (await membershipRepository().listForUser(user.id))
    .find((candidate) => candidate.status === "ACTIVE");
  const role = membership && isOrganizationRole(membership.role) ? membership.role : null;
  const assignment = membership
    ? await assignmentRepository().findPrimary(user.id, membership.organizationId)
    : null;
  const databasePermissions = role ? await rolePermissionIds(role) : { roleIds: [], permissionIds: [] };

  return {
    ...baseContext(session),
    userId: user.id,
    organizationId: membership?.organizationId ?? null,
    role,
    roleIds: databasePermissions.roleIds,
    permissions: role ? permissionsForRole(role) : [],
    permissionIds: databasePermissions.permissionIds,
    divisionId: assignment?.divisionId ?? null,
    departmentId: assignment?.departmentId ?? null,
    teamId: assignment?.teamId ?? null,
    managerUserId: assignment?.managerUserId ?? null,
  };
}
