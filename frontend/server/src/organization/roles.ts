import { permissionsForRole, type Permission } from "./permissions.js";

export const ORGANIZATION_ROLE_DEFINITIONS = [
  {
    code: "ORG_ADMIN",
    label: "Organization Admin",
    description: "Manages organization-wide users, structure, and settings.",
  },
  {
    code: "DIVISION_MANAGER",
    label: "Division Manager",
    description: "Manages resources and users within an assigned division.",
  },
  {
    code: "DEPARTMENT_MANAGER",
    label: "Department Manager",
    description: "Manages resources and users within an assigned department.",
  },
  {
    code: "TEAM_LEAD",
    label: "Team Lead",
    description: "Manages team-level resources and permitted team operations.",
  },
  {
    code: "EMPLOYEE",
    label: "Employee",
    description: "Standard organization member with permitted self and team access.",
  },
] as const satisfies readonly {
  code: string;
  label: string;
  description: string;
}[];

export type OrganizationRole = (typeof ORGANIZATION_ROLE_DEFINITIONS)[number]["code"];

export function isOrganizationRole(value: unknown): value is OrganizationRole {
  return typeof value === "string" && ORGANIZATION_ROLE_DEFINITIONS.some((role) => role.code === value);
}

export function roleWithPermissions(role: OrganizationRole) {
  const definition = ORGANIZATION_ROLE_DEFINITIONS.find((candidate) => candidate.code === role);
  return {
    ...definition,
    permissions: permissionsForRole(role) as readonly Permission[],
  };
}
