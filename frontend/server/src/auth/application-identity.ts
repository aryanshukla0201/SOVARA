import { databaseConfigured } from "../database/pool.js";
import { membershipRepository } from "../database/memberships.js";
import { userRepository } from "../database/users.js";
import { isOrganizationRole } from "../organization/roles.js";
import { permissionsForRole, type Permission } from "../organization/permissions.js";
import type { IdentityClaims } from "./oidc.js";

export type ApplicationIdentityContext = {
  userId: string | null;
  organizationId: string | null;
  role: string | null;
  permissions: readonly Permission[];
};

const emptyContext: ApplicationIdentityContext = {
  userId: null,
  organizationId: null,
  role: null,
  permissions: [],
};

export async function resolveApplicationIdentity(
  identity: IdentityClaims,
): Promise<ApplicationIdentityContext> {
  // Authentication tests and local Keycloak demos can run without PostgreSQL.
  // When configured, the application database becomes the authorization source.
  if (!databaseConfigured) return emptyContext;

  const user = await userRepository().upsertFromKeycloak({
    keycloakSubject: identity.subject,
    email: identity.email,
    username: identity.username,
    displayName: identity.displayName,
  });
  const memberships = await membershipRepository().listForUser(user.id);
  const activeMembership = memberships.find((membership) => membership.status === "ACTIVE");
  const role = activeMembership && isOrganizationRole(activeMembership.role)
    ? activeMembership.role
    : null;

  return {
    userId: user.id,
    organizationId: activeMembership?.organizationId ?? null,
    role,
    permissions: role ? permissionsForRole(role) : [],
  };
}
