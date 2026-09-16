import assert from "node:assert/strict";
import test from "node:test";
import { DatabaseSessionStore, hashSessionToken } from "../../dist/auth/session-store.js";
import { csrfTokenForSession } from "../../dist/auth/session.js";

const identity = {
  subject: "keycloak-user-001",
  email: "person@example.test",
  username: "person",
  displayName: "Person Example",
};

test("session store hashes opaque tokens before persistence", async () => {
  const calls = [];
  const pool = {
    async query(sql, params) {
      calls.push({ sql, params });
      return { rows: [] };
    },
  };
  const store = new DatabaseSessionStore(pool);

  await store.create({
    token: "opaque-session-token",
    userId: "user-1",
    identity,
    expiresAt: Date.now() + 60_000,
  });

  assert.match(calls[0].sql, /INSERT INTO sessions/);
  assert.equal(calls[0].params[2], hashSessionToken("opaque-session-token"));
  assert.notEqual(calls[0].params[2], "opaque-session-token");
});

test("session store resolves active sessions and updates last_seen_at", async () => {
  const pool = {
    async query(sql) {
      assert.match(sql, /last_seen_at = now\(\)/);
      return {
        rows: [{
          session_id: "session-row-1",
          user_id: "user-1",
          keycloak_subject: identity.subject,
          email: identity.email,
          username: identity.username,
          display_name: identity.displayName,
          created_at: new Date("2026-01-01T00:00:00.000Z"),
          expires_at: new Date(Date.now() + 60_000),
        }],
      };
    },
  };
  const stored = await new DatabaseSessionStore(pool).find("opaque-session-token");

  assert.equal(stored.userId, "user-1");
  assert.equal(stored.identity.subject, identity.subject);
  assert.equal(stored.token, "opaque-session-token");
});

test("session revocation hashes the same opaque token", async () => {
  let params;
  const pool = {
    async query(_sql, values) {
      params = values;
      return { rows: [] };
    },
  };
  await new DatabaseSessionStore(pool).revoke("opaque-session-token");
  assert.deepEqual(params, [hashSessionToken("opaque-session-token")]);
});

test("CSRF value is bound to the session token without exposing the token itself", () => {
  const csrf = csrfTokenForSession("opaque-session-token");
  assert.equal(csrf, csrfTokenForSession("opaque-session-token"));
  assert.notEqual(csrf, "opaque-session-token");
});
