import { Router, type Request, type Response, type NextFunction } from "express";
import { getSession } from "../auth/session.js";
import { requireApplicationSession } from "../auth/routes.js";
import { hasValidCsrfToken } from "../auth/session.js";
import { ORGANIZATION_ROLE_DEFINITIONS, isOrganizationRole, roleWithPermissions } from "./roles.js";
import { ORGANIZATION_PERMISSION_DEFINITIONS } from "./permissions.js";
import { HierarchyError, organizationStore } from "./store.js";

const router: Router = Router();

function body(request: Request): Record<string, unknown> {
  return request.body && typeof request.body === "object" ? request.body as Record<string, unknown> : {};
}

function text(value: unknown): string | undefined {
  return typeof value === "string" ? value : undefined;
}

function param(request: Request, key: string): string {
  const value = request.params[key];
  if (typeof value !== "string" || value.length === 0) throw new HierarchyError(`Invalid route parameter: ${key}`, 400);
  return value;
}

async function session(request: Request, response: Response) {
  try {
    return await requireApplicationSession(request);
  } catch (error) {
    const status = error instanceof Error && "status" in error ? Number((error as Error & { status: number }).status) : 401;
    response.status(status).json({ error: status === 401 ? "unauthorized" : "forbidden" });
    return null;
  }
}

async function csrf(request: Request, response: Response): Promise<boolean> {
  const current = await getSession(request);
  if (!current || !hasValidCsrfToken(current, request.get("x-csrf-token") ?? body(request).csrfToken)) {
    response.status(403).json({ error: "csrf_validation_failed" });
    return false;
  }
  return true;
}

function run(handler: (request: Request, response: Response) => unknown) {
  return async (request: Request, response: Response, next: NextFunction) => {
    try {
      await handler(request, response);
    } catch (error) {
      next(error);
    }
  };
}

router.post("/api/organizations", run(async (request, response) => {
  const current = await session(request, response);
  if (!current || !(await csrf(request, response))) return;
  const input = body(request);
  response.status(201).json(await organizationStore.createOrganization(current, {
    name: text(input.name) ?? "",
    code: text(input.code) ?? "",
    type: text(input.type) ?? null,
  }));
}));

router.get("/api/organization-roles", run(async (request, response) => {
  const current = await session(request, response);
  if (!current) return;
  response.json({ roles: ORGANIZATION_ROLE_DEFINITIONS.map((role) => roleWithPermissions(role.code as Parameters<typeof roleWithPermissions>[0])) });
}));

router.get("/api/organization-permissions", run(async (request, response) => {
  const current = await session(request, response);
  if (!current) return;
  response.json({ permissions: ORGANIZATION_PERMISSION_DEFINITIONS });
}));

router.get("/api/organizations/:organizationId", run(async (request, response) => {
  const current = await session(request, response);
  if (!current) return;
  response.json(await organizationStore.getOrganization(current, param(request, "organizationId")));
}));

router.patch("/api/organizations/:organizationId", run(async (request, response) => {
  const current = await session(request, response);
  if (!current || !(await csrf(request, response))) return;
  const input = body(request);
  response.json(await organizationStore.updateOrganization(current, param(request, "organizationId"), {
    name: text(input.name),
    type: input.type === null ? null : text(input.type),
    status: input.status === "ACTIVE" || input.status === "SUSPENDED" ? input.status : undefined,
  }));
}));

router.get("/api/organizations/:organizationId/members", run(async (request, response) => {
  const current = await session(request, response);
  if (!current) return;
  response.json(await organizationStore.listMembers(current, param(request, "organizationId")));
}));

router.post("/api/organizations/:organizationId/members", run(async (request, response) => {
  const current = await session(request, response);
  if (!current || !(await csrf(request, response))) return;
  const input = body(request);
  response.status(201).json(await organizationStore.addMember(current, param(request, "organizationId"), {
    keycloakSubject: text(input.keycloakSubject) ?? "",
    email: text(input.email) ?? null,
    username: text(input.username) ?? null,
    displayName: text(input.displayName) ?? null,
    role: isOrganizationRole(input.role) ? input.role : "EMPLOYEE",
  }));
}));

router.patch("/api/organizations/:organizationId/members/:userId", run(async (request, response) => {
  const current = await session(request, response);
  if (!current || !(await csrf(request, response))) return;
  const input = body(request);
  response.json(await organizationStore.updateMember(current, param(request, "organizationId"), param(request, "userId"), {
    role: isOrganizationRole(input.role) ? input.role : undefined,
    status: input.status === "ACTIVE" || input.status === "SUSPENDED" ? input.status : undefined,
  }));
}));

router.delete("/api/organizations/:organizationId/members/:userId", run(async (request, response) => {
  const current = await session(request, response);
  if (!current || !(await csrf(request, response))) return;
  await organizationStore.removeMember(current, param(request, "organizationId"), param(request, "userId"));
  response.status(204).end();
}));

router.get("/api/divisions/:divisionId", run(async (request, response) => {
  const current = await session(request, response);
  if (!current) return;
  response.json(await organizationStore.getDivision(current, param(request, "divisionId")));
}));

router.post("/api/organizations/:organizationId/divisions", run(async (request, response) => {
  const current = await session(request, response);
  if (!current || !(await csrf(request, response))) return;
  const input = body(request);
  response.status(201).json(await organizationStore.createDivision(current, param(request, "organizationId"), {
    name: text(input.name) ?? "",
    code: text(input.code) ?? "",
  }));
}));

router.get("/api/departments/:departmentId", run(async (request, response) => {
  const current = await session(request, response);
  if (!current) return;
  response.json(await organizationStore.getDepartment(current, param(request, "departmentId")));
}));

router.post("/api/divisions/:divisionId/departments", run(async (request, response) => {
  const current = await session(request, response);
  if (!current || !(await csrf(request, response))) return;
  const input = body(request);
  response.status(201).json(await organizationStore.createDepartment(current, param(request, "divisionId"), {
    name: text(input.name) ?? "",
    code: text(input.code) ?? "",
  }));
}));

router.get("/api/teams/:teamId", run(async (request, response) => {
  const current = await session(request, response);
  if (!current) return;
  response.json(await organizationStore.getTeam(current, param(request, "teamId")));
}));

router.post("/api/departments/:departmentId/teams", run(async (request, response) => {
  const current = await session(request, response);
  if (!current || !(await csrf(request, response))) return;
  const input = body(request);
  response.status(201).json(await organizationStore.createTeam(current, param(request, "departmentId"), {
    name: text(input.name) ?? "",
    code: text(input.code) ?? "",
  }));
}));

router.patch("/api/users/:userId/organization-assignment", run(async (request, response) => {
  const current = await session(request, response);
  if (!current || !(await csrf(request, response))) return;
  const input = body(request);
  response.json(await organizationStore.updateAssignment(current, param(request, "userId"), {
    organizationId: text(input.organizationId) ?? "",
    divisionId: input.divisionId === null ? null : text(input.divisionId),
    departmentId: input.departmentId === null ? null : text(input.departmentId),
    teamId: input.teamId === null ? null : text(input.teamId),
    managerUserId: input.managerUserId === null ? null : text(input.managerUserId),
    isPrimary: typeof input.isPrimary === "boolean" ? input.isPrimary : undefined,
  }));
}));

export { HierarchyError };
export default router;
