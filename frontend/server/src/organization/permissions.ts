import type { OrganizationRole } from "./roles.js";

export const ORGANIZATION_PERMISSION_DEFINITIONS = [
  { code: "user.read", label: "Read users", description: "View permitted application users." },
  { code: "user.create", label: "Create users", description: "Provision users into an organization." },
  { code: "user.update", label: "Update users", description: "Update permitted user records." },
  { code: "user.disable", label: "Disable users", description: "Suspend or disable permitted users." },
  { code: "organization.read", label: "Read organization", description: "View organization information." },
  { code: "organization.update", label: "Update organization", description: "Update organization settings." },
  { code: "organization.members.read", label: "Read members", description: "View organization membership." },
  { code: "organization.members.manage", label: "Manage members", description: "Add, update, assign, and remove members." },
  { code: "division.read", label: "Read divisions", description: "View permitted divisions." },
  { code: "division.manage", label: "Manage divisions", description: "Create and manage permitted divisions." },
  { code: "department.read", label: "Read departments", description: "View permitted departments." },
  { code: "department.manage", label: "Manage departments", description: "Create and manage permitted departments." },
  { code: "team.read", label: "Read teams", description: "View permitted teams." },
  { code: "team.manage", label: "Manage teams", description: "Create and manage permitted teams." },
  { code: "meeting.read", label: "Read meetings", description: "View permitted meetings." },
  { code: "meeting.create", label: "Create meetings", description: "Create permitted meetings." },
  { code: "meeting.update", label: "Update meetings", description: "Update permitted meetings." },
  { code: "meeting.delete", label: "Delete meetings", description: "Delete permitted meetings." },
  { code: "meeting.join", label: "Join meetings", description: "Join permitted meetings." },
  { code: "meeting.manage_participants", label: "Manage participants", description: "Manage permitted meeting participants." },
  { code: "chat.read", label: "Read chat", description: "Read permitted conversations." },
  { code: "chat.create", label: "Create chat", description: "Create permitted messages." },
  { code: "chat.delete", label: "Delete chat", description: "Delete permitted messages." },
  { code: "document.read", label: "Read documents", description: "Read permitted documents." },
  { code: "document.create", label: "Create documents", description: "Create permitted documents." },
  { code: "document.update", label: "Update documents", description: "Update permitted documents." },
  { code: "document.delete", label: "Delete documents", description: "Delete permitted documents." },
  { code: "artifact.read", label: "Read artifacts", description: "Read permitted artifacts." },
  { code: "artifact.create", label: "Create artifacts", description: "Create permitted artifacts." },
  { code: "admin.audit.read", label: "Read audit events", description: "View organization audit information." },
] as const;

export type Permission = (typeof ORGANIZATION_PERMISSION_DEFINITIONS)[number]["code"];

const allPermissions = ORGANIZATION_PERMISSION_DEFINITIONS.map(({ code }) => code) as Permission[];

export const ROLE_PERMISSIONS: Record<OrganizationRole, readonly Permission[]> = {
  ORG_ADMIN: allPermissions,
  DIVISION_MANAGER: [
    "user.read",
    "organization.read",
    "organization.members.read",
    "division.read",
    "division.manage",
    "department.read",
    "department.manage",
    "team.read",
    "team.manage",
    "meeting.read",
    "meeting.create",
    "meeting.update",
    "meeting.join",
    "meeting.manage_participants",
    "document.read",
    "document.create",
    "document.update",
    "artifact.read",
    "artifact.create",
  ],
  DEPARTMENT_MANAGER: [
    "user.read",
    "organization.read",
    "organization.members.read",
    "department.read",
    "department.manage",
    "team.read",
    "team.manage",
    "meeting.read",
    "meeting.create",
    "meeting.update",
    "meeting.join",
    "meeting.manage_participants",
    "document.read",
    "document.create",
    "document.update",
    "artifact.read",
    "artifact.create",
  ],
  TEAM_LEAD: [
    "user.read",
    "organization.read",
    "organization.members.read",
    "team.read",
    "team.manage",
    "meeting.read",
    "meeting.create",
    "meeting.join",
    "meeting.manage_participants",
    "document.read",
    "document.create",
    "artifact.read",
    "artifact.create",
  ],
  EMPLOYEE: [
    "organization.read",
    "organization.members.read",
    "team.read",
    "meeting.read",
    "meeting.join",
    "document.read",
    "artifact.read",
  ],
};

export function permissionsForRole(role: OrganizationRole): readonly Permission[] {
  return ROLE_PERMISSIONS[role];
}

export function hasPermission(role: OrganizationRole | null, permission: Permission): boolean {
  return role !== null && ROLE_PERMISSIONS[role].includes(permission);
}
