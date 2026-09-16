# SOVARA Server-Side Identity, Organization & Authorization Architecture

## 0. Purpose

This document defines the **server-side implementation plan** for SOVARA's:

- User authentication integration with Keycloak
- Organization management
- Organizational hierarchy
- Role and permission management
- User-to-organization membership
- Department, team, and manager relationships
- Application sessions
- Server-side authorization
- Database design
- Auditability and security boundaries
- Future extensibility

This document intentionally **does not define the AI model router, agent planner, model selection, LLM orchestration, RAG implementation, or AI model-serving internals**. Those components are owned by another team.

The server built from this document should provide a clean security and application boundary that the frontend and the AI service can consume.

---

# 1. Core Architectural Principle

SOVARA must separate four concepts:

```text
Authentication
    = Who is the person?

Organization
    = Which organization does the person belong to?

Organizational Position
    = Where does the person sit in the organization?

Authorization
    = What is the person allowed to do?
```

Do not collapse these into a single `role` field.

Example:

```text
User: Rahul Sharma

Authentication identity:
    Keycloak subject = 9f2...

Organization:
    ABC Refinery Ltd

Division:
    Refinery Operations

Department:
    Maintenance

Team:
    Mechanical Maintenance

Manager:
    Amit Verma

Role:
    ENGINEER

Permissions:
    document.read
    document.create
    meeting.create
```

The backend derives and enforces this context from the authenticated session and database. The browser must never be treated as the authority for identity, organization, role, or ownership.

---

# 2. Scope of This Server

## 2.1 This server owns

```text
Frontend/API boundary
        │
        ├── Authentication integration
        ├── Application sessions
        ├── Organization management
        ├── User management
        ├── Departments / teams
        ├── Reporting relationships
        ├── Roles / permissions
        ├── Resource authorization
        ├── Audit events
        ├── Database access
        ├── Realtime authorization boundary
        ├── WebRTC signaling authorization boundary
        └── AI-service integration boundary
```

## 2.2 This server does not own

```text
AI model routing
Agent planning
LLM orchestration
Model inference
RAG internals
Vision model internals
Prompt engineering for the AI team
```

The server may authenticate and authorize requests to those services, but it should not duplicate their internal logic.

---

# 3. Recommended Technology Boundary

Use a TypeScript-first backend.

```text
Node.js
TypeScript
NestJS
Fastify
PostgreSQL
Prisma
Redis
Keycloak
WebSocket / Socket.IO
WebRTC signaling layer
```

Recommended responsibilities:

| Technology | Responsibility |
|---|---|
| NestJS | Modular application architecture |
| Fastify | HTTP server adapter |
| Prisma | Database access and migrations |
| PostgreSQL | Application source of truth |
| Redis | Sessions, ephemeral state, rate limits, realtime coordination |
| Keycloak | Authentication and identity provider |
| Socket.IO/WebSocket | Application realtime events and WebRTC signaling |
| WebRTC | Audio/video media path |

Do not make Keycloak the application's business database.

---

# 4. Server Architecture

Use the following logical structure:

```text
                       ┌─────────────────────┐
                       │      Frontend       │
                       │   React / TypeScript │
                       └──────────┬──────────┘
                                  │ HTTPS
                                  ▼
                       ┌─────────────────────┐
                       │  SOVARA Backend     │
                       │ NestJS / Fastify    │
                       └──────────┬──────────┘
                                  │
           ┌──────────────────────┼──────────────────────┐
           │                      │                      │
           ▼                      ▼                      ▼
   Authentication           Authorization            Application
      Module                   Module                  Services
           │                      │                      │
           ▼                      ▼          ┌───────────┼───────────┐
       Keycloak               PostgreSQL     │           │           │
                                            ▼           ▼           ▼
                                         Realtime    WebRTC       AI Service
                                           Layer     Signaling    Integration
```

The backend is the **security boundary**.

---

# 5. Organizational Hierarchy

The recommended enterprise hierarchy is:

```text
Organization
│
├── Division / Business Unit
│   │
│   ├── Department
│   │   │
│   │   ├── Team / Section
│   │   │   │
│   │   │   └── Users / Employees
│   │   │   │
│   │   │   └── Team Lead
│   │   │
│   │   └── Department Manager
│   │
│   └── Division Head
│
└── Organization Admin
```

This is a **data hierarchy**, not an authentication protocol.

Authentication remains:

```text
Person
  ↓
Keycloak
  ↓
Verified identity
  ↓
Application user
  ↓
Organization membership
  ↓
Role + permissions + organizational scope
```

---

# 6. Roles vs Organizational Position

Never encode the hierarchy only as roles.

Bad design:

```text
MECHANICAL_ENGINEER_UNDER_MAINTENANCE_MANAGER
```

Good design:

```text
role          = ENGINEER
department_id = maintenance
team_id       = mechanical-maintenance
manager_id    = manager-123
```

Recommended initial roles:

```text
ORG_ADMIN
DIVISION_MANAGER
DEPARTMENT_MANAGER
TEAM_LEAD
EMPLOYEE
```

Optional future roles:

```text
SECURITY_ADMIN
AUDITOR
SYSTEM_OPERATOR
COMPLIANCE_OFFICER
MEETING_MODERATOR
```

Roles describe authority. Organizational relationships describe structure.

---

# 7. Permission Model

Use permissions as atomic capabilities.

Example:

```text
user.read
user.create
user.update
user.disable

organization.read
organization.update

organization.members.read
organization.members.manage

department.read
department.manage

team.read
team.manage

meeting.read
meeting.create
meeting.update
meeting.delete
meeting.join
meeting.manage_participants

chat.read
chat.create
chat.delete

document.read
document.create
document.update
document.delete

artifact.read
artifact.create

admin.audit.read
```

A role should map to permissions rather than every controller containing hard-coded role logic.

Example:

```text
TEAM_LEAD
    ├── team.read
    ├── team.manage
    ├── user.read
    ├── meeting.create
    ├── meeting.manage_participants
    └── document.read
```

Use a centralized authorization service to evaluate these permissions.

---

# 8. Authorization Scope

A permission alone is not enough.

The backend should evaluate both:

```text
Capability + Scope
```

Example:

```text
permission = document.read
scope      = own_team
```

A manager may have:

```text
user.read + department_scope
```

An organization admin may have:

```text
user.read + organization_scope
```

This prevents a valid permission from becoming a global permission accidentally.

Recommended scopes:

```text
SELF
OWN_TEAM
OWN_DEPARTMENT
OWN_DIVISION
OWN_ORGANIZATION
SYSTEM
```

Future applications may add resource-specific ACLs on top of these scopes.

---

# 9. Database Source of Truth

PostgreSQL is the application's source of truth.

Keycloak owns:

```text
Authentication credentials
Identity
OIDC sessions
Realm configuration
Keycloak roles / groups
```

PostgreSQL owns:

```text
Organization
Users
Memberships
Departments
Teams
Reporting relationships
Application roles / permissions
Conversations
Meetings
Documents metadata
Artifacts metadata
Audit events
Application sessions or session references
```

Never store raw passwords in PostgreSQL.

---

# 10. Core Database Model

Start with these entities.

```text
organizations
users
organization_memberships
divisions
departments
teams
roles
permissions
role_permissions
user_roles
sessions
audit_logs
```

Later, add:

```text
conversations
messages
meetings
meeting_participants
realtime_presence
webrtc_sessions
webrtc_participants
documents
artifacts
ai_service_runs
```

---

# 11. Organization Table

Recommended fields:

```text
organizations
------------------------------
id                  UUID PK
name                VARCHAR
code                VARCHAR UNIQUE
type                VARCHAR
status              ENUM
created_at          TIMESTAMP
updated_at          TIMESTAMP
```

Example:

```text
id:   org_001
name: ABC Refinery Ltd
code: ABC-REF
type: REFINERY
status: ACTIVE
```

`code` should be unique and stable enough for administration, but internal foreign keys should use the UUID/primary key.

---

# 12. User Table

Recommended fields:

```text
users
------------------------------
id                  UUID PK
keycloak_subject    VARCHAR UNIQUE
email               VARCHAR NULL
username            VARCHAR NULL
display_name        VARCHAR
status              ENUM
created_at          TIMESTAMP
updated_at          TIMESTAMP
last_login_at       TIMESTAMP NULL
```

Important:

```text
keycloak_subject = stable external identity mapping
```

Do not use email as the permanent identity key.

---

# 13. Organization Membership

Do not assume one organization forever.

Use a membership table even if SOVARA initially supports one organization per user.

```text
organization_memberships
------------------------------
id                    UUID PK
user_id               UUID FK
organization_id       UUID FK
status                ENUM
joined_at             TIMESTAMP
left_at               TIMESTAMP NULL
```

Add a unique constraint appropriate to the product rule, for example:

```text
UNIQUE(user_id, organization_id)
```

This gives you a clean path toward multi-tenancy later.

---

# 14. Division / Department / Team Tables

## Division

```text
divisions
------------------------------
id                  UUID PK
organization_id     UUID FK
name                VARCHAR
code                VARCHAR
created_at          TIMESTAMP
updated_at          TIMESTAMP
```

## Department

```text
departments
------------------------------
id                  UUID PK
division_id         UUID FK
name                VARCHAR
code                VARCHAR
created_at          TIMESTAMP
updated_at          TIMESTAMP
```

## Team

```text
teams
------------------------------
id                  UUID PK
department_id       UUID FK
name                VARCHAR
code                VARCHAR
created_at          TIMESTAMP
updated_at          TIMESTAMP
```

Foreign keys should enforce the organizational hierarchy.

---

# 15. User Organizational Position

Keep organizational placement on a dedicated relationship rather than making the user table a dumping ground.

Recommended entity:

```text
user_organizational_assignments
------------------------------
id                  UUID PK
user_id             UUID FK
organization_id     UUID FK
division_id         UUID FK NULL
department_id       UUID FK NULL
team_id             UUID FK NULL
manager_user_id     UUID FK NULL
is_primary          BOOLEAN
valid_from          TIMESTAMP
valid_until         TIMESTAMP NULL
created_at          TIMESTAMP
```

This design has two major advantages:

1. A user can move between teams without destroying historical information.
2. Future support for temporary assignments or multiple organizational memberships becomes possible.

Do not start by adding dozens of hierarchy columns directly to `users` unless the product requirements force that simplicity.

---

# 16. Reporting Relationship

The direct reporting relationship is represented by:

```text
manager_user_id
```

Example:

```text
Amit
  │
  ├── Rahul
  ├── Neha
  └── Arjun
```

The backend should be able to answer:

```text
Who is my manager?
Who reports to me?
Who belongs under my department?
Who belongs under my team?
```

Do not trust the frontend to send a manager relationship.

All management relationships must be created or modified through authorized backend operations.

---

# 17. Keycloak Integration Model

Use Keycloak as the identity provider.

Recommended flow:

```text
Browser
   ↓
GET /api/auth/login
   ↓
Backend
   ↓
Keycloak Authorization Endpoint
   ↓
User Authentication
   ↓
Keycloak Callback
   ↓
Backend
   ↓
Validate identity
   ↓
Find users.keycloak_subject
   ↓
Load organization membership
   ↓
Load roles / permissions
   ↓
Create application session
   ↓
HttpOnly session cookie
```

Use OIDC Authorization Code + PKCE.

The backend should own the code exchange and session creation.

---

# 18. Authentication Data vs Authorization Data

## Keycloak should provide

```text
sub
iss
email / username where configured
identity claims
Keycloak roles / groups where required
```

## Application database should provide

```text
application user ID
organization membership
division
department
team
manager
application roles
application permissions
ownership
resource scope
account status
```

Do not overload the ID token with the entire application hierarchy.

The token identifies the principal; the database provides application context.

---

# 19. Application Session

After Keycloak login, create an application-owned session.

Browser:

```text
__Host-sovara_session=<opaque-value>
```

The cookie should be:

```text
HttpOnly
Secure          # outside localhost development
SameSite=Lax
Path=/
No Domain
```

The browser should not receive long-lived Keycloak client secrets or refresh tokens.

The backend resolves the session to the authenticated application user.

---

# 20. Authentication Context

Create a single server-side request context type.

Example:

```ts
export interface AuthContext {
  sessionId: string;
  userId: string;
  keycloakSubject: string;
  organizationId: string;
  roleIds: string[];
  permissionIds: string[];
  divisionId?: string;
  departmentId?: string;
  teamId?: string;
  managerUserId?: string;
}
```

Do not pass this object from the frontend.

The backend constructs it from:

```text
session
  ↓
verified identity
  ↓
database
  ↓
authorized organizational context
```

---

# 21. Authorization Pipeline

Every protected request should follow this pattern:

```text
HTTP Request
    ↓
Session extraction
    ↓
Session validation
    ↓
Authenticated user resolution
    ↓
Organization membership resolution
    ↓
Permission check
    ↓
Scope / ownership check
    ↓
Business operation
    ↓
Audit event if required
    ↓
Response
```

Never do this:

```text
Request
  ↓
body.userId
  ↓
execute database query
```

Correct:

```text
Request
  ↓
session.userId
  ↓
authorization policy
  ↓
query scoped to authorized organization/resource
```

---

# 22. Central Authorization Service

Do not implement authorization independently inside every controller.

Create a centralized authorization module.

Example interface:

```ts
can(
  auth: AuthContext,
  action: Permission,
  resource?: ResourceContext,
): Promise<boolean>;
```

Example:

```ts
await authorization.can(
  auth,
  'document.read',
  {
    organizationId: document.organizationId,
    departmentId: document.departmentId,
    ownerUserId: document.ownerUserId,
  },
);
```

The policy evaluates:

```text
Does the user have the permission?
Does the user's role grant it?
Is the resource inside the user's organization?
Is the resource inside their scope?
Is the user the owner?
Is the operation allowed for the resource state?
```

Default decision:

```text
DENY
```

---

# 23. Example Authorization Rules

## Employee

```text
Can read own profile
Can read permitted team documents
Can join permitted meetings
Can create permitted meetings
Cannot manage organization users
Cannot change organization roles
Cannot access another organization's data
```

## Team Lead

```text
Everything an employee can do
+
Read team members
Manage team-level resources
Manage permitted meetings
```

## Department Manager

```text
Everything below department scope
+
Manage department users where permitted
Manage department resources
View department-level information
```

## Organization Admin

```text
Organization-wide management
+
Manage organization users
Manage departments / teams
Assign organizational roles
View organization audit information
```

Never assume that a role automatically means unrestricted access.

---

# 24. Multi-Tenant Safety

Even if the initial deployment has only one organization, design every business query so organization boundaries are explicit.

Example:

```ts
where: {
  organizationId: auth.organizationId,
  id: documentId,
}
```

Prefer service methods that require an authorization context:

```ts
getDocument(auth: AuthContext, documentId: string)
```

Avoid methods like:

```ts
getDocument(documentId: string)
```

for protected business data.

This makes cross-organization data leakage harder to introduce accidentally.

---

# 25. API Structure

Organize APIs by domain.

```text
/api/auth/*
/api/organizations/*
/api/users/*
/api/divisions/*
/api/departments/*
/api/teams/*
/api/meetings/*
/api/conversations/*
/api/documents/*
/api/artifacts/*
/api/realtime/*
/api/webrtc/*
/api/ai/*
/api/audit/*
```

Do not create one enormous controller.

---

# 26. Authentication API

Recommended endpoints:

```text
GET    /api/auth/login
GET    /api/auth/callback/keycloak
GET    /api/auth/session
POST   /api/auth/logout
GET    /api/auth/csrf
```

Responsibilities:

```text
login       → start OIDC transaction
callback    → validate OIDC response and create application session
session     → return frontend-safe current-user information
logout      → invalidate application session
csrf        → provide CSRF mechanism where required
```

---

# 27. Organization APIs

Recommended administrative API shape:

```text
GET    /api/organizations/:organizationId
PATCH  /api/organizations/:organizationId

GET    /api/organizations/:organizationId/members
POST   /api/organizations/:organizationId/members
PATCH  /api/organizations/:organizationId/members/:userId
DELETE /api/organizations/:organizationId/members/:userId
```

Do not allow clients to choose arbitrary organizations.

The backend must verify that the authenticated user has the required organization-level permission.

---

# 28. Hierarchy APIs

Recommended resources:

```text
GET    /api/divisions/:divisionId
POST   /api/organizations/:organizationId/divisions

GET    /api/departments/:departmentId
POST   /api/divisions/:divisionId/departments

GET    /api/teams/:teamId
POST   /api/departments/:departmentId/teams
```

For assignments:

```text
PATCH /api/users/:userId/organization-assignment
```

The backend validates every parent-child relationship.

For example:

```text
team.department_id
    must belong to

assignment.department_id
    which must belong to

assignment.division_id
    which must belong to

assignment.organization_id
```

Reject inconsistent hierarchy assignments.

---

# 29. User Provisioning Strategy

For the initial enterprise implementation:

```text
Organization Admin
        ↓
Create / invite user
        ↓
Keycloak identity created or linked
        ↓
Application user created
        ↓
Organization membership created
        ↓
Department/team assigned
        ↓
Role assigned
        ↓
User can sign in
```

Do not expose unrestricted public organization signup for a sensitive enterprise deployment.

A future self-service onboarding system can be introduced later with explicit approval workflows.

---

# 30. User Deactivation

Do not physically delete users by default.

Use:

```text
status = ACTIVE | SUSPENDED | DISABLED
```

Deactivation should:

```text
Disable application access
Invalidate application sessions
Prevent realtime connections
Prevent WebRTC signaling access
Prevent privileged API calls
Optionally disable the corresponding Keycloak user
```

Preserve audit history.

---

# 31. Audit Logging

Create a dedicated audit module.

Record security-sensitive actions such as:

```text
LOGIN_SUCCESS
LOGIN_FAILURE
LOGOUT
SESSION_CREATED
SESSION_REVOKED
USER_CREATED
USER_DISABLED
ROLE_CHANGED
PERMISSION_CHANGED
ORGANIZATION_MEMBERSHIP_CHANGED
DEPARTMENT_ASSIGNMENT_CHANGED
MANAGER_CHANGED
DOCUMENT_ACCESS
MEETING_CREATED
MEETING_JOINED
WEBRTC_SESSION_CREATED
AI_SERVICE_REQUESTED
```

Prefer metadata over storing sensitive content in logs.

Never log:

```text
Passwords
Client secrets
Refresh tokens
Session secrets
Raw confidential documents
Private meeting media
Sensitive prompts unless explicitly required and protected
```

---

# 32. Realtime Authorization Boundary

Socket.IO/WebSocket connections should authenticate using the application session.

Connection flow:

```text
Client
   ↓
Socket connection
   ↓
Backend session validation
   ↓
Resolve AuthContext
   ↓
Authorize channel / room
   ↓
Connection accepted
```

Do not allow a client to subscribe to arbitrary rooms such as:

```text
organization:123
user:456
meeting:789
```

without checking authorization.

---

# 33. Room Authorization

Every realtime room should have a backend-defined policy.

Examples:

```text
user:{userId}
team:{teamId}
department:{departmentId}
meeting:{meetingId}
conversation:{conversationId}
```

Example rule:

```text
meeting:{id}

Allowed only when:
    user is meeting owner
    OR user is an authorized participant
    OR user has the required management permission
```

Never trust a room ID as proof of membership.

---

# 34. WebRTC Server Boundary

The backend should own **signaling authorization**, not the WebRTC media itself.

Conceptually:

```text
Frontend
   │
   │ Socket.IO / signaling
   ▼
SOVARA Backend
   │
   ├── authenticate
   ├── authorize meeting
   ├── exchange SDP offers/answers
   ├── exchange ICE candidates
   └── manage participant state
            │
            ▼
        WebRTC peers / future SFU
```

The backend must verify:

```text
Who is connecting?
Which meeting are they joining?
Are they a participant?
Are they allowed to publish media?
Are they allowed to receive media?
```

Do not put authorization logic in the browser only.

---

# 35. WebRTC Data Model

Recommended starting entities:

```text
meetings
------------------------------
id
organization_id
created_by
status
scheduled_at
created_at
updated_at
```

```text
meeting_participants
------------------------------
id
meeting_id
user_id
role
status
joined_at
left_at
```

```text
webrtc_sessions
------------------------------
id
meeting_id
user_id
connection_id
status
created_at
closed_at
```

The exact media architecture may later evolve from peer-to-peer to an SFU without changing the core identity system.

---

# 36. AI Service Integration Boundary

The AI team owns the model router and agent system.

Your backend should expose a controlled internal integration boundary.

```text
Frontend
   ↓
SOVARA Backend
   ↓
Authentication
   ↓
Authorization
   ↓
Create AI request context
   ↓
AI Service
```

The backend should send only information the authenticated user is permitted to send.

Example internal request context:

```json
{
  "requestId": "req_123",
  "userId": "usr_123",
  "organizationId": "org_001",
  "departmentId": "dept_01",
  "teamId": "team_03",
  "permissions": [
    "document.read"
  ]
}
```

Do not allow the frontend to directly call the internal AI service unless there is a deliberate, separately secured architecture.

---

# 37. Permission-Aware Data Access

The backend must authorize access **before** passing confidential content to another service.

Correct flow:

```text
User request
    ↓
Authenticate
    ↓
Authorize
    ↓
Fetch permitted documents/data
    ↓
Pass only permitted context to AI service
```

Incorrect flow:

```text
AI service receives entire organization database
    ↓
AI decides what user should see
```

Authorization belongs to the application backend, not to the LLM.

---

# 38. Clean Code / Module Structure

Recommended NestJS structure:

```text
src/
│
├── main.ts
├── app.module.ts
│
├── config/
│   ├── env.config.ts
│   └── validation.ts
│
├── common/
│   ├── decorators/
│   ├── guards/
│   ├── interceptors/
│   ├── filters/
│   ├── pipes/
│   ├── errors/
│   └── types/
│
├── auth/
│   ├── auth.module.ts
│   ├── controllers/
│   ├── services/
│   ├── guards/
│   ├── strategies/
│   ├── session/
│   └── dto/
│
├── authorization/
│   ├── authorization.module.ts
│   ├── authorization.service.ts
│   ├── policies/
│   ├── permissions.ts
│   └── scopes.ts
│
├── organizations/
│   ├── organizations.module.ts
│   ├── organizations.controller.ts
│   ├── organizations.service.ts
│   └── dto/
│
├── users/
├── memberships/
├── divisions/
├── departments/
├── teams/
├── meetings/
├── realtime/
├── webrtc/
├── ai-gateway/
├── audit/
│
├── database/
│   ├── prisma.service.ts
│   └── repositories/
│
└── health/
```

Keep modules independently testable.

---

# 39. Layer Responsibilities

Use four logical layers inside each feature where practical:

```text
Controller
   ↓
Application Service
   ↓
Domain / Policy
   ↓
Repository
   ↓
Database
```

Example:

```text
PATCH /users/:id/assignment
        ↓
UsersController
        ↓
UserAssignmentService
        ↓
AuthorizationPolicy
        ↓
UserRepository / OrganizationRepository
        ↓
PostgreSQL
```

Controllers should remain thin.

Do not put complex database logic or authorization rules directly into controllers.

---

# 40. Repository Rules

Repositories should handle persistence, not authorization.

Good:

```ts
organizationRepository.findById(id)
```

Authorization service decides whether the caller can use the result.

Even better for protected operations:

```ts
userRepository.findVisibleUsers(authContext, filters)
```

The application layer should make authorization scope explicit so unsafe calls are difficult to write.

---

# 41. Validation

Validate every external input.

Use DTOs and a schema validation library such as Zod where appropriate.

Validate:

```text
UUIDs
Emails
Organization codes
Enum values
Pagination
Sorting
Date ranges
Meeting IDs
Socket event payloads
WebRTC signaling payloads
```

Never trust TypeScript types as runtime validation.

---

# 42. Error Model

Use consistent errors.

Recommended:

```text
401 Unauthorized
    → no valid authenticated session

403 Forbidden
    → authenticated but insufficient permission

404 Not Found
    → resource does not exist OR intentionally hidden

409 Conflict
    → hierarchy / membership / state conflict

422 Unprocessable Entity
    → invalid semantic input

429 Too Many Requests
    → rate limit exceeded
```

Do not leak unnecessary internal information in authorization errors.

---

# 43. Security Rules

## Mandatory

```text
[ ] Keycloak client secret is server-only
[ ] No auth tokens in localStorage
[ ] Application session is HttpOnly
[ ] Session IDs rotate after login
[ ] CSRF protection exists for cookie-authenticated state changes
[ ] Origin / CORS is restricted
[ ] Authorization happens server-side
[ ] Tenant / organization scope is enforced in data queries
[ ] Default authorization decision is DENY
[ ] Keycloak issuer/signature/audience/expiration checks are enabled
[ ] Keycloak admin interface is not publicly exposed
[ ] Secrets are never committed to Git
[ ] Realtime room access is server-authorized
[ ] WebRTC signaling is server-authorized
[ ] AI requests pass through an authorization boundary
[ ] Audit events do not contain secrets or unnecessary confidential payloads
```

---

# 44. Rate Limiting

Protect at least:

```text
/api/auth/login
/api/auth/callback/*
/api/auth/logout
user-management endpoints
organization-management endpoints
meeting creation
WebSocket connection attempts
WebRTC signaling events
AI gateway endpoints
```

Use Redis for distributed rate-limit state when multiple backend instances are deployed.

---

# 45. Transaction Rules

Use database transactions when multiple security-related records must change together.

Example user provisioning:

```text
Create application user
    ↓
Create organization membership
    ↓
Create organizational assignment
    ↓
Assign application role
    ↓
Commit
```

If any step fails, rollback the transaction.

External Keycloak actions must be treated carefully because they are not part of the PostgreSQL transaction. Design provisioning as an explicit workflow with retry and reconciliation behavior.

---

# 46. Idempotency

Administrative operations and external integrations should be safe to retry.

Use idempotency keys where appropriate for:

```text
user provisioning
meeting creation
AI service request submission
artifact creation requests
webhook-like internal callbacks
```

Avoid duplicate resources when a client retries after a network failure.

---

# 47. State Machines

Avoid ambiguous booleans for complex lifecycle states.

Example meeting:

```text
DRAFT
  ↓
SCHEDULED
  ↓
LIVE
  ↓
ENDED
  ↓
ARCHIVED
```

Example user:

```text
INVITED
  ↓
ACTIVE
  ↓
SUSPENDED
  ↓
DISABLED
```

Keep state transitions server-controlled.

---

# 48. Observability

Every important request should have a correlation/request ID.

Example:

```text
requestId = req_01J...
```

Use structured logs.

Track metrics such as:

```text
login success/failure
active sessions
WebSocket connections
WebRTC signaling failures
API latency
authorization denials
PostgreSQL latency
Redis latency
AI gateway latency
```

Do not log confidential payloads merely for debugging convenience.

---

# 49. Testing Strategy

Testing should mirror the security boundary.

## Unit tests

Test:

```text
authorization policies
permission mapping
scope calculation
hierarchy validation
session behavior
input validation
state transitions
```

## Integration tests

Test against PostgreSQL and a Keycloak test environment:

```text
login
callback
session creation
session expiration
role resolution
organization membership
manager assignment
```

## Security tests

Explicitly verify:

```text
User A cannot access User B's data
Organization A cannot access Organization B's data
Employee cannot invoke admin operations
Team Lead cannot modify another department
Disabled users cannot reconnect over WebSocket
Non-participants cannot join meetings
Unauthorized users cannot access WebRTC signaling
Frontend-supplied role cannot elevate privileges
Frontend-supplied organizationId cannot escape tenant scope
```

---

# 50. Migration Strategy

Do not introduce Keycloak while maintaining two independent session authorities indefinitely.

Migration sequence:

```text
1. Configure Keycloak realm
2. Configure confidential backend client
3. Implement OIDC login flow
4. Implement application session
5. Implement current-user endpoint
6. Implement authorization context
7. Create organization/user database mapping
8. Migrate protected routes
9. Migrate frontend auth integration
10. Migrate realtime authentication
11. Migrate WebRTC signaling authorization
12. Route AI requests through backend authorization
13. Remove legacy authentication
```

There must eventually be one application authentication source of truth.

---

# 51. Development Order

Build this in small vertical slices.

## Phase 1 — Backend foundation

```text
Create NestJS project
Configure Fastify
Configure environment validation
Configure PostgreSQL
Configure Prisma
Create migration workflow
Add global error handling
Add structured logging
```

## Phase 2 — Organization database

```text
organizations
users
organization_memberships
divisions
departments
teams
user_organizational_assignments
```

Create constraints and indexes before building many endpoints.

## Phase 3 — Keycloak

```text
Create realm
Create backend client
Configure OIDC
Configure redirect URI
Implement login
Implement callback
Validate tokens
```

## Phase 4 — Application session

```text
Create session store
Create secure cookie
Implement /api/auth/session
Implement logout
Implement session revocation
```

## Phase 5 — Authorization

```text
Create permissions
Create roles
Create role_permissions
Create user_roles
Create AuthContext
Create AuthorizationService
Create guards / decorators
```

## Phase 6 — Organization administration

```text
Create organization APIs
Create user provisioning
Create memberships
Create departments
Create teams
Create manager assignments
```

## Phase 7 — Realtime

```text
Authenticate Socket.IO connections
Create authorized rooms
Implement presence
Implement application realtime events
```

## Phase 8 — WebRTC signaling

```text
Authorize meeting join
Create signaling events
Exchange SDP
Exchange ICE candidates
Track connections
Close unauthorized / expired sessions
```

## Phase 9 — AI integration boundary

```text
Create internal AI gateway
Authenticate service-to-service requests
Propagate requestId
Pass authorization context
Enforce document/data scope
Return AI-service results to frontend
```

## Phase 10 — Hardening

```text
Rate limits
CSRF
CORS restrictions
Security headers
Audit logging
Metrics
Backup / restore
Integration tests
Security tests
```

---

# 52. Future Management Scope

Design the schema so the following can be added without redesigning authentication:

```text
Multiple organizations
Multiple divisions
Matrix reporting
Temporary assignments
Delegated administration
Custom roles
Permission groups
Resource-level ACLs
Document classification
Project-level memberships
Meeting moderators
Security administrators
Auditors
MFA / WebAuthn
LDAP / Active Directory integration
SSO federation
Service accounts
Machine-to-machine authorization
```

The important rule is:

```text
Authentication should remain stable
while authorization and organizational structure evolve.
```

---

# 53. Recommended Ownership Model

Your team should own:

```text
Authentication integration
Application sessions
User database
Organization hierarchy
RBAC / permissions
Authorization policies
Realtime gateway
WebRTC signaling authorization
Frontend-facing APIs
AI service gateway
Audit trail
```

Your teammate's AI system should own:

```text
Task analysis
Model routing
Agent planning
Model invocation
AI orchestration
```

The contract between both systems should be an internal API boundary, not shared implementation logic.

---

# 54. Final Security Architecture

```text
                           USER
                            │
                            ▼
                     React Frontend
                            │
                            │ HTTPS
                            ▼
                  ┌─────────────────────┐
                  │   SOVARA BACKEND    │
                  │ NestJS + Fastify    │
                  └──────────┬──────────┘
                             │
          ┌──────────────────┼───────────────────┐
          │                  │                   │
          ▼                  ▼                   ▼
      AUTH MODULE       AUTHORIZATION       APPLICATION
          │                  │                SERVICES
          ▼                  ▼                   │
      Keycloak         Roles + Scopes           │
                             │                   │
                             ├──────────┬────────┘
                             │          │
                             ▼          ▼
                        PostgreSQL    Redis
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
          Realtime         WebRTC       AI Gateway
          Socket.IO       Signaling          │
                                             ▼
                                        AI Team Service
```

The key trust boundary is:

```text
              USER INPUT
                  │
                  ▼
        ┌───────────────────┐
        │    BACKEND        │
        │                   │
        │ Authenticate      │
        │ Authorize         │
        │ Scope             │
        │ Validate          │
        │ Audit             │
        └─────────┬─────────┘
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
   Application          AI Service
      Data               Service
```

**The frontend presents authority; it does not define authority.**

**Keycloak authenticates the identity; the backend defines application authorization.**

**PostgreSQL defines organizational membership and application state.**

**Realtime/WebRTC access is authorized by the backend.**

**The AI service receives only data and requests that the authenticated user is permitted to access.**

---

# 55. Implementation Definition of Done

Do not consider the server-side identity architecture complete until all of the following are true:

```text
[ ] User can authenticate through Keycloak
[ ] Backend creates an application session
[ ] Frontend can retrieve the authenticated user
[ ] User maps to a PostgreSQL application record
[ ] User belongs to an organization
[ ] User can be assigned to a division / department / team
[ ] User can have a manager
[ ] Role and permissions are resolved server-side
[ ] Authorization is centralized
[ ] Organization scope is enforced in database access
[ ] Unauthorized users receive 403
[ ] Unauthenticated users receive 401
[ ] Disabled users cannot access protected APIs
[ ] WebSocket connections require authentication
[ ] WebSocket rooms require authorization
[ ] WebRTC signaling requires meeting authorization
[ ] AI requests pass through an authorization gateway
[ ] Audit logs capture security-sensitive changes
[ ] Secrets are excluded from source control and logs
[ ] Rate limiting is enabled on sensitive endpoints
[ ] Security and cross-tenant tests pass
```

---

# 56. Build Rule

Build the backend in this order:

```text
Database
   ↓
Authentication
   ↓
Session
   ↓
Authorization
   ↓
Organization hierarchy
   ↓
User management
   ↓
Realtime
   ↓
WebRTC signaling
   ↓
AI gateway
```

Do not start by building dozens of frontend screens.

The frontend should consume a stable server contract.

Do not start by building the AI integration.

The AI team should consume a stable, authenticated and authorization-aware internal contract.

The **server-side identity + organization + authorization layer is the foundation on which every other SOVARA feature should sit.**
