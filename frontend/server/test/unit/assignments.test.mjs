import assert from "node:assert/strict";
import test from "node:test";
import { AssignmentRepository } from "../../dist/database/assignments.js";

const baseRow = {
  id: "assignment-1",
  user_id: "user-1",
  organization_id: "org-1",
  division_id: "division-1",
  department_id: "department-1",
  team_id: "team-1",
  manager_user_id: "manager-1",
  is_primary: true,
  valid_from: new Date("2026-01-01T00:00:00.000Z"),
  valid_until: null,
  created_at: new Date("2026-01-01T00:00:00.000Z"),
};

test("assignment repository closes the previous primary assignment transactionally", async () => {
  const calls = [];
  const client = {
    async query(sql, params) {
      calls.push({ sql, params });
      if (sql.startsWith("INSERT")) return { rows: [{ ...baseRow }] };
      return { rows: [] };
    },
    release() {},
  };
  const pool = { async connect() { return client; } };
  const repository = new AssignmentRepository(pool);

  const assignment = await repository.create({
    userId: "user-1",
    organizationId: "org-1",
    divisionId: "division-1",
    departmentId: "department-1",
    teamId: "team-1",
    managerUserId: "manager-1",
  });

  assert.equal(assignment.isPrimary, true);
  assert.equal(calls[0].sql, "BEGIN");
  assert.ok(calls.some((call) => call.sql.includes("SET is_primary = false")));
  assert.ok(calls.some((call) => call.sql.includes("INSERT INTO user_organizational_assignments")));
  assert.equal(calls.at(-1).sql, "COMMIT");
});

test("assignment history allows non-primary records and reports are current-only", async () => {
  const calls = [];
  const client = {
    async query(sql) {
      calls.push({ sql });
      if (sql.startsWith("INSERT")) return { rows: [{ ...baseRow, is_primary: false }] };
      return { rows: [] };
    },
    release() {},
  };
  const repository = new AssignmentRepository({ async connect() { return client; } });

  const historical = await repository.create({ userId: "user-1", organizationId: "org-1", isPrimary: false });
  assert.equal(historical.isPrimary, false);
  assert.match(calls[1].sql, /INSERT INTO user_organizational_assignments/);

  const reportPool = {
    async query(sql, params) {
      calls.push({ sql, params });
      return { rows: [] };
    },
  };
  await new AssignmentRepository(reportPool).listReports("manager-1", "org-1");
  assert.match(calls.at(-1).sql, /valid_until IS NULL/);
});

test("assignment repository rejects self-management before opening a transaction", async () => {
  let connected = false;
  const repository = new AssignmentRepository({
    async connect() {
      connected = true;
      throw new Error("should not connect");
    },
  });

  await assert.rejects(
    () => repository.create({ userId: "user-1", organizationId: "org-1", managerUserId: "user-1" }),
    /managerUserId cannot equal userId/,
  );
  assert.equal(connected, false);
});

test("assignment repository rejects reporting cycles", async () => {
  const client = {
    async query(sql) {
      if (sql === "BEGIN") return { rows: [] };
      if (sql.startsWith("WITH RECURSIVE")) return { rows: [{ '?column?': 1 }], rowCount: 1 };
      return { rows: [] };
    },
    release() {},
  };
  const repository = new AssignmentRepository({ async connect() { return client; } });

  await assert.rejects(
    () => repository.create({ userId: "user-1", organizationId: "org-1", managerUserId: "manager-1" }),
    /reporting cycle/,
  );
});

test("reporting queries are organization-scoped and only include current assignments", async () => {
  const calls = [];
  const repository = new AssignmentRepository({
    async query(sql, params) {
      calls.push({ sql, params });
      return { rows: [] };
    },
  });

  await repository.findManager("user-1", "org-1");
  await repository.listDirectReportUsers("manager-1", "org-1");
  await repository.listDepartmentUsers("department-1", "org-1");
  await repository.listTeamUsers("team-1", "org-1");

  assert.equal(calls.length, 4);
  assert.ok(calls.every((call) => call.sql.includes("organization_id = $2")));
  assert.ok(calls.every((call) => call.sql.includes("valid_until IS NULL")));
});
