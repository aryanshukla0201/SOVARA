import assert from "node:assert/strict";
import test from "node:test";
import { resolveApplicationIdentity } from "../../dist/auth/application-identity.js";

test("application identity keeps Keycloak-only local mode available without a database", async () => {
  const context = await resolveApplicationIdentity({
    subject: "keycloak-user-001",
    email: "person@example.test",
    username: "person",
    displayName: "Person Example",
  });

  assert.deepEqual(context, {
    userId: null,
    organizationId: null,
    role: null,
    permissions: [],
  });
});
