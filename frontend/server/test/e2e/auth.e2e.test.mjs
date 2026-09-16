/** @typedef {import('node:http').Server} HttpServer */
/** @typedef {import('node:http').IncomingMessage} IncomingMessage */
/** @typedef {import('node:http').ServerResponse} ServerResponse */
/** @typedef {import('node:child_process').ChildProcess} AppProcess */
/** @typedef {import('jose').KeyLike} KeyLike */
/** @typedef {{ nonce: string, challenge: string }} KeycloakLoginState */

import assert from "node:assert/strict";
import { createServer } from "node:http";
import { once } from "node:events";
import { spawn } from "node:child_process";
import { createHash, randomBytes } from "node:crypto";
import { after, before, describe, test } from "node:test";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import {
  exportJWK,
  generateKeyPair,
  SignJWT,
} from "jose";

const serverRoot = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const frontendOrigin = "http://localhost:8080";

/** @type {HttpServer | undefined} */
let keycloakServer;
/** @type {AppProcess | undefined} */
let applicationProcess;
/** @type {string} */
let keycloakOrigin;
/** @type {string} */
let applicationOrigin;
/** @type {KeycloakLoginState | undefined} */
let keycloakState;
/** @type {KeyLike | undefined} */
let signingKey;
/** @type {KeyLike | undefined} */
let verificationKey;
/** @type {Record<string, unknown> | undefined} */
let publicJwk;
/** @type {string | null | undefined} */
let codeVerifier;

function randomString(bytes = 24) {
  return randomBytes(bytes).toString("base64url");
}

/** @param {IncomingMessage} request */
function readForm(request) {
  return new Promise((resolve, reject) => {
    let body = "";
    request.setEncoding("utf8");
    request.on("data", (chunk) => {
      body += chunk;
    });
    request.on("end", () => resolve(new URLSearchParams(body)));
    request.on("error", reject);
  });
}

/** @param {ServerResponse} response */
/** @param {number} status */
/** @param {Record<string, unknown>} value */
function json(response, status, value) {
  response.writeHead(status, { "content-type": "application/json" });
  response.end(JSON.stringify(value));
}

/** @param {HttpServer} server */
function startServer(server) {
  server.listen(0, "127.0.0.1");
  return once(server, "listening").then(() => {
    const address = server.address();
    assert.ok(address && typeof address === "object");
    return `http://127.0.0.1:${address.port}`;
  });
}

async function waitForHealth(url) {
  const deadline = Date.now() + 10_000;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(`${url}/health`);
      if (response.ok) return;
    } catch {
      // The child process may still be starting.
    }
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw new Error(`Application did not become healthy at ${url}`);
}

/** @param {AppProcess | undefined} child */
async function stopProcess(child) {
  if (!child || child.exitCode !== null) return;
  child.kill();
  await once(child, "exit");
}

function cookiePair(response) {
  const cookies = response.headers.getSetCookie?.() ?? [];
  const value = cookies[0] ?? response.headers.get("set-cookie");
  assert.ok(value, "Expected the application to set a session cookie");
  return value.split(";", 1)[0];
}

async function createIdToken(nonce) {
  return new SignJWT({
    sub: "keycloak-user-001",
    nonce,
    email: "rahul@example.test",
    preferred_username: "rahul",
    name: "Rahul Sharma",
  })
    .setProtectedHeader({ alg: "RS256", kid: "test-key-1", typ: "JWT" })
    .setIssuer(keycloakOrigin + "/realms/sovara-local")
    .setAudience("sovara-backend-local")
    .setIssuedAt()
    .setExpirationTime("5m")
    .sign(signingKey);
}

before(async () => {
  ({ privateKey: signingKey, publicKey: verificationKey } = await generateKeyPair("RS256"));
  publicJwk = await exportJWK(verificationKey);
  publicJwk.kid = "test-key-1";
  publicJwk.alg = "RS256";
  publicJwk.use = "sig";

  keycloakServer = createServer(async (request, response) => {
    const requestUrl = new URL(request.url, "http://localhost");
    const issuer = `${keycloakOrigin}/realms/sovara-local`;

    if (requestUrl.pathname === "/realms/sovara-local/.well-known/openid-configuration") {
      json(response, 200, {
        issuer,
        authorization_endpoint: `${keycloakOrigin}/realms/sovara-local/protocol/openid-connect/auth`,
        token_endpoint: `${keycloakOrigin}/realms/sovara-local/protocol/openid-connect/token`,
        userinfo_endpoint: `${keycloakOrigin}/realms/sovara-local/protocol/openid-connect/userinfo`,
        end_session_endpoint: `${keycloakOrigin}/realms/sovara-local/protocol/openid-connect/logout`,
        jwks_uri: `${keycloakOrigin}/realms/sovara-local/protocol/openid-connect/certs`,
      });
      return;
    }

    if (requestUrl.pathname.endsWith("/protocol/openid-connect/certs")) {
      json(response, 200, { keys: [publicJwk] });
      return;
    }

    if (requestUrl.pathname.endsWith("/protocol/openid-connect/auth")) {
      const redirectUri = requestUrl.searchParams.get("redirect_uri");
      const state = requestUrl.searchParams.get("state");
      const nonce = requestUrl.searchParams.get("nonce");
      const challenge = requestUrl.searchParams.get("code_challenge");
      assert.equal(requestUrl.searchParams.get("code_challenge_method"), "S256");
      assert.ok(redirectUri && state && nonce && challenge);
      keycloakState = { nonce, challenge };
      const callback = new URL(redirectUri);
      callback.searchParams.set("code", "test-authorization-code");
      callback.searchParams.set("state", state);
      response.writeHead(302, { location: callback.toString() });
      response.end();
      return;
    }

    if (requestUrl.pathname.endsWith("/protocol/openid-connect/token")) {
      const form = await readForm(request);
      assert.equal(form.get("client_id"), "sovara-backend-local");
      assert.equal(form.get("client_secret"), "test-client-secret");
      assert.equal(form.get("code"), "test-authorization-code");
      codeVerifier = form.get("code_verifier");
      assert.ok(codeVerifier);
      const derivedChallenge = createHash("sha256").update(codeVerifier).digest("base64url");
      assert.equal(derivedChallenge, keycloakState.challenge);
      json(response, 200, {
        access_token: "test-access-token",
        token_type: "Bearer",
        expires_in: 300,
        id_token: await createIdToken(keycloakState.nonce),
      });
      return;
    }

    if (requestUrl.pathname.endsWith("/protocol/openid-connect/userinfo")) {
      assert.equal(request.headers.authorization, "Bearer test-access-token");
      json(response, 200, {
        sub: "keycloak-user-001",
        email: "rahul@example.test",
        preferred_username: "rahul",
        name: "Rahul Sharma",
      });
      return;
    }

    if (requestUrl.pathname.endsWith("/protocol/openid-connect/logout")) {
      response.writeHead(302, { location: frontendOrigin + "/" });
      response.end();
      return;
    }

    json(response, 404, { error: "not_found" });
  });
  keycloakOrigin = await startServer(keycloakServer);

  const appPortServer = createServer();
  applicationOrigin = await startServer(appPortServer);
  appPortServer.close();
  await once(appPortServer, "close");

  const applicationPort = new URL(applicationOrigin).port;
  applicationProcess = spawn(process.execPath, [join(serverRoot, "dist", "index.js")], {
    cwd: serverRoot,
    env: {
      ...process.env,
      SERVER_PORT: applicationPort,
      FRONTEND_ORIGIN: frontendOrigin,
      KEYCLOAK_ISSUER: `${keycloakOrigin}/realms/sovara-local`,
      KEYCLOAK_CLIENT_ID: "sovara-backend-local",
      KEYCLOAK_CLIENT_SECRET: "test-client-secret",
      KEYCLOAK_REDIRECT_URI: `${applicationOrigin}/api/auth/callback/keycloak`,
      KEYCLOAK_POST_LOGOUT_REDIRECT_URI: `${frontendOrigin}/`,
      ORGANIZATION_BOOTSTRAP_SUBJECT: "keycloak-user-001",
      ORG_STORE_MODE: "memory",
      SESSION_COOKIE_SECURE: "true",
    },
    stdio: ["ignore", "pipe", "pipe"],
  });
  applicationProcess.stderr.setEncoding("utf8");
  applicationProcess.stderr.on("data", (chunk) => {
    process.stderr.write(`[app] ${chunk}`);
  });
  await waitForHealth(applicationOrigin);
});

after(async () => {
  await stopProcess(applicationProcess);
  keycloakServer?.close();
});

describe("Keycloak authentication flow", () => {
  test("rejects an unauthenticated session", async () => {
    const response = await fetch(`${applicationOrigin}/api/auth/session`);
    assert.equal(response.status, 401);
    assert.deepEqual(await response.json(), { authenticated: false });
  });

  test("rejects a callback with an unknown state", async () => {
    const response = await fetch(
      `${applicationOrigin}/api/auth/callback/keycloak?code=bad&state=unknown`,
    );
    assert.equal(response.status, 400);
    assert.deepEqual(await response.json(), { error: "invalid_login_callback" });
  });

  test("performs login, verifies the ID token, and creates a session", async () => {
    const login = await fetch(
      `${applicationOrigin}/api/auth/login?returnTo=/workbench`,
      { redirect: "manual" },
    );
    assert.equal(login.status, 302);
    const keycloakLoginUrl = login.headers.get("location");
    assert.ok(keycloakLoginUrl);
    assert.match(keycloakLoginUrl, /code_challenge_method=S256/);

    const keycloakLogin = await fetch(keycloakLoginUrl, { redirect: "manual" });
    assert.equal(keycloakLogin.status, 302);
    const callbackUrl = keycloakLogin.headers.get("location");
    assert.ok(callbackUrl);

    const callback = await fetch(callbackUrl, { redirect: "manual" });
    assert.equal(callback.status, 302);
    assert.equal(callback.headers.get("location"), `${frontendOrigin}/workbench`);
    const cookie = cookiePair(callback);

    const session = await fetch(`${applicationOrigin}/api/auth/session`, {
      headers: { cookie },
    });
    assert.equal(session.status, 200);
    const body = await session.json();
    assert.equal(body.authenticated, true);
    assert.equal(body.user.keycloakSubject, "keycloak-user-001");
    assert.equal(body.user.email, "rahul@example.test");
    assert.ok(body.csrfToken);

    const rolesResponse = await fetch(`${applicationOrigin}/api/organization-roles`, {
      headers: { cookie },
    });
    assert.equal(rolesResponse.status, 200);
    const rolesBody = await rolesResponse.json();
    assert.deepEqual(
      rolesBody.roles.map((role) => role.code),
      ["ORG_ADMIN", "DIVISION_MANAGER", "DEPARTMENT_MANAGER", "TEAM_LEAD", "EMPLOYEE"],
    );
    const teamLeadRole = rolesBody.roles.find((role) => role.code === "TEAM_LEAD");
    assert.ok(teamLeadRole.permissions.includes("team.manage"));
    assert.ok(!teamLeadRole.permissions.includes("organization.members.manage"));

    const permissionsResponse = await fetch(`${applicationOrigin}/api/organization-permissions`, {
      headers: { cookie },
    });
    assert.equal(permissionsResponse.status, 200);
    const permissionsBody = await permissionsResponse.json();
    assert.ok(permissionsBody.permissions.some((permission) => permission.code === "document.read"));
    assert.ok(permissionsBody.permissions.some((permission) => permission.code === "organization.members.manage"));

    const jsonHeaders = {
      cookie,
      "content-type": "application/json",
      "x-csrf-token": body.csrfToken,
    };
    const createOrganization = await fetch(`${applicationOrigin}/api/organizations`, {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({ name: "ABC Refinery Ltd", code: "abc-ref", type: "REFINERY" }),
    });
    assert.equal(createOrganization.status, 201);
    const organization = await createOrganization.json();
    assert.equal(organization.code, "ABC-REF");

    const createDivision = await fetch(
      `${applicationOrigin}/api/organizations/${organization.id}/divisions`,
      {
        method: "POST",
        headers: jsonHeaders,
        body: JSON.stringify({ name: "Refinery Operations", code: "ops" }),
      },
    );
    assert.equal(createDivision.status, 201);
    const division = await createDivision.json();
    assert.equal(division.organizationId, organization.id);

    const createDepartment = await fetch(
      `${applicationOrigin}/api/divisions/${division.id}/departments`,
      {
        method: "POST",
        headers: jsonHeaders,
        body: JSON.stringify({ name: "Maintenance", code: "maint" }),
      },
    );
    assert.equal(createDepartment.status, 201);
    const department = await createDepartment.json();
    assert.equal(department.divisionId, division.id);

    const createTeam = await fetch(
      `${applicationOrigin}/api/departments/${department.id}/teams`,
      {
        method: "POST",
        headers: jsonHeaders,
        body: JSON.stringify({ name: "Mechanical Maintenance", code: "mech" }),
      },
    );
    assert.equal(createTeam.status, 201);
    const team = await createTeam.json();
    assert.equal(team.departmentId, department.id);

    const addMember = await fetch(
      `${applicationOrigin}/api/organizations/${organization.id}/members`,
      {
        method: "POST",
        headers: jsonHeaders,
        body: JSON.stringify({
          keycloakSubject: "keycloak-user-002",
          email: "neha@example.test",
          username: "neha",
          displayName: "Neha Singh",
          role: "TEAM_LEAD",
        }),
      },
    );
    assert.equal(addMember.status, 201);
    const member = await addMember.json();
    assert.equal(member.membership.organizationId, organization.id);
    assert.equal(member.membership.role, "TEAM_LEAD");

    const assignMember = await fetch(
      `${applicationOrigin}/api/users/${member.user.id}/organization-assignment`,
      {
        method: "PATCH",
        headers: jsonHeaders,
        body: JSON.stringify({
          organizationId: organization.id,
          divisionId: division.id,
          departmentId: department.id,
          teamId: team.id,
          managerUserId: body.user.keycloakSubject === "keycloak-user-001" ? member.user.id : null,
        }),
      },
    );
    assert.equal(assignMember.status, 200);
    const assignment = await assignMember.json();
    assert.equal(assignment.teamId, team.id);

    const changeRole = await fetch(
      `${applicationOrigin}/api/organizations/${organization.id}/members/${member.user.id}`,
      {
        method: "PATCH",
        headers: jsonHeaders,
        body: JSON.stringify({ role: "DEPARTMENT_MANAGER" }),
      },
    );
    assert.equal(changeRole.status, 200);
    const changedMember = await changeRole.json();
    assert.equal(changedMember.membership.role, "DEPARTMENT_MANAGER");
    const membersAfterRoleChange = await fetch(
      `${applicationOrigin}/api/organizations/${organization.id}/members`,
      { headers: { cookie } },
    );
    assert.equal(membersAfterRoleChange.status, 200);
    const membersBody = await membersAfterRoleChange.json();
    assert.ok(Array.isArray(membersBody), JSON.stringify(membersBody));
    const changedMemberContext = membersBody.find(
      (entry) => entry.user?.keycloakSubject === "keycloak-user-002",
    );
    assert.ok(changedMemberContext, "Updated member was not returned by the members endpoint");
    assert.equal(changedMemberContext.role, "DEPARTMENT_MANAGER");
    assert.equal(changedMemberContext.assignment.teamId, team.id);

    const otherDepartmentResponse = await fetch(
      `${applicationOrigin}/api/divisions/${division.id}/departments`,
      {
        method: "POST",
        headers: jsonHeaders,
        body: JSON.stringify({ name: "Safety", code: "safety" }),
      },
    );
    assert.equal(otherDepartmentResponse.status, 201);
    const otherDepartment = await otherDepartmentResponse.json();
    const otherTeamResponse = await fetch(
      `${applicationOrigin}/api/departments/${otherDepartment.id}/teams`,
      {
        method: "POST",
        headers: jsonHeaders,
        body: JSON.stringify({ name: "Safety Team", code: "safety-team" }),
      },
    );
    assert.equal(otherTeamResponse.status, 201);
    const otherTeam = await otherTeamResponse.json();

    const inconsistentAssignment = await fetch(
      `${applicationOrigin}/api/users/${member.user.id}/organization-assignment`,
      {
        method: "PATCH",
        headers: jsonHeaders,
        body: JSON.stringify({
          organizationId: organization.id,
          divisionId: division.id,
          departmentId: department.id,
          teamId: otherTeam.id,
        }),
      },
    );
    assert.equal(inconsistentAssignment.status, 409);

    const csrfFailure = await fetch(`${applicationOrigin}/api/auth/logout`, {
      method: "POST",
      headers: { cookie },
    });
    assert.equal(csrfFailure.status, 403);

    const logout = await fetch(`${applicationOrigin}/api/auth/logout`, {
      method: "POST",
      headers: { cookie, "x-csrf-token": body.csrfToken },
    });
    assert.equal(logout.status, 200);
    const logoutBody = await logout.json();
    assert.equal(logoutBody.loggedOut, true);
    assert.match(logoutBody.logoutUrl, /openid-connect\/logout/);

    const afterLogout = await fetch(`${applicationOrigin}/api/auth/session`, {
      headers: { cookie },
    });
    assert.equal(afterLogout.status, 401);
  });
});
