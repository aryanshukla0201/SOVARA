import assert from "node:assert/strict";
import test from "node:test";
import { OrganizationRepository } from "../../dist/database/organizations.js";

const baseRow = {
  id: "org-1",
  name: "ABC Refinery Ltd",
  code: "ABC-REF",
  type: "REFINERY",
  status: "ACTIVE",
  created_at: new Date("2026-01-01T00:00:00.000Z"),
  updated_at: new Date("2026-01-01T00:00:00.000Z"),
};

test("organization repository normalizes codes and maps database rows", async () => {
  const queries = [];
  const pool = {
    async query(sql, params) {
      queries.push({ sql, params });
      return { rows: [{ ...baseRow }] };
    },
  };

  const repository = new OrganizationRepository(pool);
  const organization = await repository.create({
    name: "ABC Refinery Ltd",
    code: "abc-ref",
    type: "REFINERY",
  });

  assert.equal(organization.code, "ABC-REF");
  assert.match(queries[0].sql, /INSERT INTO organizations/);
  assert.equal(queries[0].params[1], "ABC Refinery Ltd");
  assert.equal(queries[0].params[2], "ABC-REF");
});

test("organization repository can explicitly clear the optional type", async () => {
  const calls = [];
  const pool = {
    async query(sql, params) {
      calls.push({ sql, params });
      return { rows: [{ ...baseRow, type: null }] };
    },
  };

  const repository = new OrganizationRepository(pool);
  const organization = await repository.update("org-1", { type: null });

  assert.equal(organization.type, null);
  assert.equal(calls[0].params[2], true);
  assert.equal(calls[0].params[3], null);
});

test("organization repository rejects blank required values before querying", async () => {
  let called = false;
  const repository = new OrganizationRepository({
    async query() {
      called = true;
      return { rows: [] };
    },
  });

  await assert.rejects(() => repository.create({ name: " ", code: "ABC" }), /name is required/);
  assert.equal(called, false);
});
