import assert from "node:assert/strict";
import test from "node:test";
import { resolveAuthContext } from "../../dist/auth/context.js";
import { createSession } from "../../dist/auth/session.js";

test("auth context keeps Keycloak identity separate from authorization data", async () => {
  const session = createSession({
    subject: "keycloak-user-001",
    email: "person@example.test",
    username: "person",
    displayName: "Person Example",
  });
  const context = await resolveAuthContext(session);

  assert.equal(context.keycloakSubject, "keycloak-user-001");
  assert.equal(context.email, "person@example.test");
  assert.equal(context.userId, null);
  assert.equal(context.organizationId, null);
  assert.equal(context.role, null);
  assert.deepEqual(context.permissions, []);
  assert.deepEqual(context.roleIds, []);
  assert.deepEqual(context.permissionIds, []);
});
