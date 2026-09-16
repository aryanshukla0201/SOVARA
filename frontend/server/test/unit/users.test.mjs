import assert from "node:assert/strict";
import test from "node:test";
import { UserRepository } from "../../dist/database/users.js";

const baseRow = {
  id: "user-1",
  keycloak_subject: "kc-subject-1",
  email: "person@example.com",
  username: "person",
  display_name: "Person Example",
  status: "ACTIVE",
  created_at: new Date("2026-01-01T00:00:00.000Z"),
  updated_at: new Date("2026-01-01T00:00:00.000Z"),
  last_login_at: new Date("2026-01-01T00:00:00.000Z"),
};

test("user repository upserts by stable Keycloak subject", async () => {
  const calls = [];
  const pool = {
    async query(sql, params) {
      calls.push({ sql, params });
      return { rows: [{ ...baseRow }] };
    },
  };

  const repository = new UserRepository(pool);
  const user = await repository.upsertFromKeycloak({
    keycloakSubject: " kc-subject-1 ",
    email: " person@example.com ",
    username: " person ",
    displayName: " Person Example ",
  });

  assert.equal(user.keycloakSubject, "kc-subject-1");
  assert.match(calls[0].sql, /ON CONFLICT \(keycloak_subject\)/);
  assert.equal(calls[0].params[1], "kc-subject-1");
  assert.equal(calls[0].params[2], "person@example.com");
});

test("user repository preserves nullable profile fields and supports status updates", async () => {
  const calls = [];
  const pool = {
    async query(sql, params) {
      calls.push({ sql, params });
      return { rows: [{ ...baseRow, email: null, status: "SUSPENDED" }] };
    },
  };

  const repository = new UserRepository(pool);
  const user = await repository.update("user-1", { email: null, status: "SUSPENDED" });

  assert.equal(user.email, null);
  assert.equal(user.status, "SUSPENDED");
  assert.equal(calls[0].params[1], true);
  assert.equal(calls[0].params[2], null);
});

test("user repository rejects an empty Keycloak subject", async () => {
  let called = false;
  const repository = new UserRepository({
    async query() {
      called = true;
      return { rows: [] };
    },
  });

  await assert.rejects(
    () => repository.findByKeycloakSubject(" "),
    /keycloakSubject is required/,
  );
  assert.equal(called, false);
});
