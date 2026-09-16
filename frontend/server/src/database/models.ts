export type OrganizationStatus = "ACTIVE" | "SUSPENDED";
export type UserStatus = "ACTIVE" | "SUSPENDED" | "DISABLED";
export type MembershipStatus = "ACTIVE" | "SUSPENDED" | "LEFT";

export type OrganizationRecord = {
  id: string;
  name: string;
  code: string;
  type: string | null;
  status: OrganizationStatus;
  createdAt: Date;
  updatedAt: Date;
};

export type UserRecord = {
  id: string;
  keycloakSubject: string;
  email: string | null;
  username: string | null;
  displayName: string | null;
  status: UserStatus;
  createdAt: Date;
  updatedAt: Date;
  lastLoginAt: Date | null;
};

export type OrganizationMembershipRecord = {
  id: string;
  userId: string;
  organizationId: string;
  role: string;
  status: MembershipStatus;
  joinedAt: Date;
  leftAt: Date | null;
};

export type DivisionRecord = {
  id: string;
  organizationId: string;
  name: string;
  code: string;
  createdAt: Date;
  updatedAt: Date;
};

export type DepartmentRecord = {
  id: string;
  divisionId: string;
  name: string;
  code: string;
  createdAt: Date;
  updatedAt: Date;
};

export type TeamRecord = {
  id: string;
  departmentId: string;
  name: string;
  code: string;
  createdAt: Date;
  updatedAt: Date;
};

export type OrganizationalAssignmentRecord = {
  id: string;
  userId: string;
  organizationId: string;
  divisionId: string | null;
  departmentId: string | null;
  teamId: string | null;
  managerUserId: string | null;
  isPrimary: boolean;
  validFrom: Date;
  validUntil: Date | null;
  createdAt: Date;
};

export type ApplicationSessionRecord = {
  id: string;
  userId: string;
  tokenHash: string;
  expiresAt: Date;
  revokedAt: Date | null;
  createdAt: Date;
  lastSeenAt: Date;
  ipAddress: string | null;
  userAgent: string | null;
};

export type AuditLogRecord = {
  id: string;
  organizationId: string | null;
  actorUserId: string | null;
  action: string;
  resourceType: string;
  resourceId: string | null;
  metadata: Record<string, unknown>;
  createdAt: Date;
};
