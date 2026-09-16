import assert from "node:assert/strict";
import { test } from "node:test";
import { can, scopeForPermission } from "../../dist/organization/authorization.js";

const context = (role, overrides = {}) => ({
  sessionId: "session-1",
  userId: "user-1",
  keycloakSubject: "subject-1",
  organizationId: "org-1",
  role,
  divisionId: "division-1",
  departmentId: "department-1",
  teamId: "team-1",
  managerUserId: null,
  ...overrides,
});

test("division manager permissions are limited to the assigned division", () => {
  const auth = context("DIVISION_MANAGER");
  assert.equal(scopeForPermission("DIVISION_MANAGER", "department.manage"), "OWN_DIVISION");
  assert.equal(can(auth, "department.manage", {
    organizationId: "org-1",
    divisionId: "division-1",
  }), true);
  assert.equal(can(auth, "department.manage", {
    organizationId: "org-1",
    divisionId: "division-2",
  }), false);
  assert.equal(can(auth, "organization.update", { organizationId: "org-1" }), false);
});

test("department and team scopes remain distinct", () => {
  const departmentManager = context("DEPARTMENT_MANAGER");
  assert.equal(scopeForPermission("DEPARTMENT_MANAGER", "team.manage"), "OWN_DEPARTMENT");
  assert.equal(can(departmentManager, "team.manage", {
    organizationId: "org-1",
    departmentId: "department-1",
  }), true);
  assert.equal(can(departmentManager, "team.manage", {
    organizationId: "org-1",
    departmentId: "department-2",
  }), false);

  const teamLead = context("TEAM_LEAD");
  assert.equal(scopeForPermission("TEAM_LEAD", "team.manage"), "OWN_TEAM");
  assert.equal(can(teamLead, "team.manage", {
    organizationId: "org-1",
    departmentId: "department-1",
    teamId: "team-1",
  }), true);
  assert.equal(can(teamLead, "team.manage", {
    organizationId: "org-1",
    departmentId: "department-1",
    teamId: "team-2",
  }), false);
});

test("employee document access is team-scoped and ownership remains separate", () => {
  const auth = context("EMPLOYEE");
  assert.equal(scopeForPermission("EMPLOYEE", "document.read"), "OWN_TEAM");
  assert.equal(can(auth, "document.read", {
    organizationId: "org-1",
    teamId: "team-1",
    ownerUserId: "user-2",
  }), true);
  assert.equal(can(auth, "document.read", {
    organizationId: "org-1",
    teamId: "team-2",
    ownerUserId: "user-1",
  }), false);
});
