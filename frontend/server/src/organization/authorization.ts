import { hasPermission, type Permission, ROLE_PERMISSIONS } from "./permissions.js";
import type { AuthContext, OrganizationRole } from "./types.js";

export type AuthorizationScope =
  | "SELF"
  | "OWN_TEAM"
  | "OWN_DEPARTMENT"
  | "OWN_DIVISION"
  | "OWN_ORGANIZATION"
  | "SYSTEM";

export type ResourceContext = {
  organizationId: string;
  divisionId?: string | null | undefined;
  departmentId?: string | null | undefined;
  teamId?: string | null | undefined;
  ownerUserId?: string | null | undefined;
};

const organizationReadPermissions = new Set<Permission>(["organization.read"]);
const divisionScopedPermissions = new Set<Permission>([
  "user.read", "organization.members.read", "division.read", "division.manage",
  "department.read", "department.manage", "team.read", "team.manage",
  "meeting.read", "meeting.create", "meeting.update", "meeting.join",
  "meeting.manage_participants", "document.read", "document.create",
  "document.update", "artifact.read", "artifact.create",
]);
const departmentScopedPermissions = new Set<Permission>([
  "user.read", "organization.members.read", "department.read", "department.manage",
  "team.read", "team.manage", "meeting.read", "meeting.create", "meeting.update",
  "meeting.join", "meeting.manage_participants", "document.read", "document.create",
  "document.update", "artifact.read", "artifact.create",
]);
const teamScopedPermissions = new Set<Permission>([
  "user.read", "organization.members.read", "team.read", "team.manage",
  "meeting.read", "meeting.create", "meeting.join", "meeting.manage_participants",
  "document.read", "document.create", "artifact.read", "artifact.create",
]);
const employeeTeamScopedPermissions = new Set<Permission>([
  "organization.members.read",
  "team.read",
  "meeting.read",
  "meeting.join",
  "document.read",
  "artifact.read",
]);

export function scopeForPermission(role: OrganizationRole, permission: Permission): AuthorizationScope {
  if (role === "ORG_ADMIN") return "OWN_ORGANIZATION";
  if (organizationReadPermissions.has(permission)) return "OWN_ORGANIZATION";
  if (role === "DIVISION_MANAGER" && divisionScopedPermissions.has(permission)) return "OWN_DIVISION";
  if (role === "DEPARTMENT_MANAGER" && departmentScopedPermissions.has(permission)) return "OWN_DEPARTMENT";
  if (role === "TEAM_LEAD" && teamScopedPermissions.has(permission)) return "OWN_TEAM";
  if (role === "EMPLOYEE" && employeeTeamScopedPermissions.has(permission)) return "OWN_TEAM";
  return "SELF";
}

export function scopeAllows(auth: AuthContext, scope: AuthorizationScope, resource: ResourceContext): boolean {
  if (scope === "SYSTEM") return auth.role === "ORG_ADMIN" && auth.organizationId === null;
  if (auth.organizationId !== resource.organizationId) return false;
  if (scope === "OWN_ORGANIZATION") return true;
  if (scope === "OWN_DIVISION") return Boolean(auth.divisionId && resource.divisionId === auth.divisionId);
  if (scope === "OWN_DEPARTMENT") return Boolean(auth.departmentId && resource.departmentId === auth.departmentId);
  if (scope === "OWN_TEAM") return Boolean(auth.teamId && resource.teamId === auth.teamId);
  return Boolean(auth.userId && resource.ownerUserId === auth.userId);
}

export function can(auth: AuthContext, permission: Permission, resource: ResourceContext): boolean {
  const configuredPermissions = auth.permissions ?? [];
  const permissionGranted = configuredPermissions.length > 0
    ? configuredPermissions.includes(permission)
    : Boolean(auth.role && hasPermission(auth.role, permission));
  return Boolean(auth.role && permissionGranted && scopeAllows(auth, scopeForPermission(auth.role, permission), resource));
}

export function permissionsForContext(auth: AuthContext): readonly Permission[] {
  const configuredPermissions = auth.permissions ?? [];
  return configuredPermissions.length > 0 ? configuredPermissions : auth.role ? ROLE_PERMISSIONS[auth.role] : [];
}
