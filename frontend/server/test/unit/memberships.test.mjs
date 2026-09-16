import assert from "node:assert/strict";
import test from "node:test";
import { MembershipRepository } from "../../dist/database/memberships.js";

const baseRow = {
  id: "membership-1",
  user_id: "user-1",
  organization_id: "org-1",
  role: "EMPLOYEE",
  status: "ACTIVE",
  joined_at: new Date("2026-01-01T00:00:00.000Z"),
  left_at: null,
};

test("membership repository keeps one membership per user and organization", async () => {
  const calls = [];
  const pool = {
    async query(sql, params) {
      calls.push({ sql, params });
      return { rows: [{ ...baseRow }] };
    },
  };

  const repository = new MembershipRepository(pool);
  const membership = await repository.add({
    userId: " user-1 ",
    organizationId: " org-1 ",
    role: " EMPLOYEE ",
  });

  assert.equal(membership.userId, "user-1");
  assert.equal(membership.organizationId, "org-1");
  assert.match(calls[0].sql, /ON CONFLICT \(user_id, organization_id\)/);
  assert.deepEqual(calls[0].params.slice(1), ["user-1", "org-1", "EMPLOYEE"]);
});

test("membership repository sets and clears left_at with lifecycle status", async () => {
  const calls = [];
  const pool = {
    async query(sql, params) {
      calls.push({ sql, params });
      return { rows: [{ ...baseRow, status: params[2], left_at: params[2] === "LEFT" ? new Date() : null }] };
    },
  };

  const repository = new MembershipRepository(pool);
  const left = await repository.setStatus("user-1", "org-1", "LEFT");
  const active = await repository.setStatus("user-1", "org-1", "ACTIVE");

  assert.equal(left.status, "LEFT");
  assert.notEqual(left.leftAt, null);
  assert.equal(active.status, "ACTIVE");
  assert.equal(active.leftAt, null);
  assert.equal(calls[0].params[2], "LEFT");
  assert.equal(calls[1].params[2], "ACTIVE");
});

test("membership repository rejects missing identifiers", async () => {
  let called = false;
  const repository = new MembershipRepository({
    async query() {
      called = true;
      return { rows: [] };
    },
  });

  await assert.rejects(
    () => repository.add({ userId: "", organizationId: "org-1", role: "EMPLOYEE" }),
    /userId is required/,
  );
  assert.equal(called, false);
});
