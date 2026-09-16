export type OrganizationStatus = "ACTIVE" | "SUSPENDED";
export type MembershipStatus = "ACTIVE" | "SUSPENDED" | "LEFT";
export type UserStatus = "ACTIVE" | "SUSPENDED" | "DISABLED";
export type { OrganizationRole } from "./roles.js";
import type { OrganizationRole } from "./roles.js";
import type { Permission } from "./permissions.js";

export type Organization = {
  id: string;
  name: string;
  code: string;
  type: string | null;
  status: OrganizationStatus;
  createdAt: string;
  updatedAt: string;
};

export type Division = {
  id: string;
  organizationId: string;
  name: string;
  code: string;
  createdAt: string;
  updatedAt: string;
};

export type Department = {
  id: string;
  divisionId: string;
  name: string;
  code: string;
  createdAt: string;
  updatedAt: string;
};

export type Team = {
  id: string;
  departmentId: string;
  name: string;
  code: string;
  createdAt: string;
  updatedAt: string;
};

export type ApplicationUser = {
  id: string;
  keycloakSubject: string;
  email: string | null;
  username: string | null;
  displayName: string | null;
  status: UserStatus;
  createdAt: string;
  updatedAt: string;
};

export type OrganizationMembership = {
  id: string;
  userId: string;
  organizationId: string;
  role: OrganizationRole;
  status: MembershipStatus;
  joinedAt: string;
  leftAt: string | null;
};

export type OrganizationalAssignment = {
  id: string;
  userId: string;
  organizationId: string;
  divisionId: string | null;
  departmentId: string | null;
  teamId: string | null;
  managerUserId: string | null;
  isPrimary: boolean;
  validFrom: string;
  validUntil: string | null;
  createdAt: string;
};

export type AuthContext = {
  sessionId: string;
  userId: string | null;
  keycloakSubject: string;
  organizationId: string | null;
  role: OrganizationRole | null;
  divisionId: string | null;
  departmentId: string | null;
  teamId: string | null;
  managerUserId: string | null;
  permissions: readonly Permission[];
};
