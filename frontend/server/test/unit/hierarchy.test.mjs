import assert from "node:assert/strict";
import test from "node:test";
import { HierarchyRepository } from "../../dist/database/hierarchy.js";

const row = {
  id: "node-1",
  organization_id: "org-1",
  division_id: "division-1",
  department_id: "department-1",
  name: "Operations",
  code: "OPS",
  created_at: new Date("2026-01-01T00:00:00.000Z"),
  updated_at: new Date("2026-01-01T00:00:00.000Z"),
};

test("hierarchy repository creates nodes with normalized codes and parent IDs", async () => {
  const calls = [];
  const pool = {
    async query(sql, params) {
      calls.push({ sql, params });
      if (sql.includes("INSERT INTO departments")) return { rows: [{ ...row, division_id: params[1] }] };
      if (sql.includes("INSERT INTO teams")) return { rows: [{ ...row, department_id: params[1] }] };
      return { rows: [{ ...row }] };
    },
  };

  const repository = new HierarchyRepository(pool);
  const division = await repository.createDivision("org-1", { name: "Operations", code: " ops " });
  const department = await repository.createDepartment("division-1", { name: "Refining", code: "ref" });
  const team = await repository.createTeam("department-1", { name: "Shift A", code: "shift-a" });

  assert.equal(division.code, "OPS");
  assert.equal(department.divisionId, "division-1");
  assert.equal(team.departmentId, "department-1");
  assert.equal(calls[1].params[3], "REF");
  assert.equal(calls[2].params[3], "SHIFT-A");
});

test("hierarchy repository scopes child listings to their direct parent", async () => {
  const calls = [];
  const pool = {
    async query(sql, params) {
      calls.push({ sql, params });
      return { rows: [] };
    },
  };

  const repository = new HierarchyRepository(pool);
  await repository.listDivisions("org-1");
  await repository.listDepartments("division-1");
  await repository.listTeams("department-1");

  assert.deepEqual(calls.map((call) => call.params[0]), ["org-1", "division-1", "department-1"]);
});

test("hierarchy repository rejects blank parent identifiers", async () => {
  let called = false;
  const repository = new HierarchyRepository({
    async query() {
      called = true;
      return { rows: [] };
    },
  });

  await assert.rejects(
    () => repository.createTeam("", { name: "Shift A", code: "A" }),
    /departmentId is required/,
  );
  assert.equal(called, false);
});
