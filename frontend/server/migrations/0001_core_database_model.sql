CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS organizations (
  id UUID PRIMARY KEY,
  name VARCHAR(200) NOT NULL,
  code VARCHAR(80) NOT NULL UNIQUE,
  type VARCHAR(80),
  status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'SUSPENDED')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY,
  keycloak_subject VARCHAR(255) NOT NULL UNIQUE,
  email VARCHAR(320),
  username VARCHAR(255),
  display_name VARCHAR(255),
  status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'SUSPENDED', 'DISABLED')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_login_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS organization_memberships (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id),
  organization_id UUID NOT NULL REFERENCES organizations(id),
  role VARCHAR(40) NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'SUSPENDED', 'LEFT')),
  joined_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  left_at TIMESTAMPTZ,
  UNIQUE (user_id, organization_id)
);

CREATE TABLE IF NOT EXISTS divisions (
  id UUID PRIMARY KEY,
  organization_id UUID NOT NULL REFERENCES organizations(id),
  name VARCHAR(200) NOT NULL,
  code VARCHAR(80) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (organization_id, code)
);

CREATE TABLE IF NOT EXISTS departments (
  id UUID PRIMARY KEY,
  division_id UUID NOT NULL REFERENCES divisions(id),
  name VARCHAR(200) NOT NULL,
  code VARCHAR(80) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (division_id, code)
);

CREATE TABLE IF NOT EXISTS teams (
  id UUID PRIMARY KEY,
  department_id UUID NOT NULL REFERENCES departments(id),
  name VARCHAR(200) NOT NULL,
  code VARCHAR(80) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (department_id, code)
);

CREATE TABLE IF NOT EXISTS user_organizational_assignments (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id),
  organization_id UUID NOT NULL REFERENCES organizations(id),
  division_id UUID REFERENCES divisions(id),
  department_id UUID REFERENCES departments(id),
  team_id UUID REFERENCES teams(id),
  manager_user_id UUID REFERENCES users(id),
  is_primary BOOLEAN NOT NULL DEFAULT true,
  valid_from TIMESTAMPTZ NOT NULL DEFAULT now(),
  valid_until TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (valid_until IS NULL OR valid_until > valid_from),
  UNIQUE (user_id, organization_id, is_primary)
);

CREATE TABLE IF NOT EXISTS roles (
  id UUID PRIMARY KEY,
  code VARCHAR(80) NOT NULL UNIQUE,
  description TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS permissions (
  id UUID PRIMARY KEY,
  code VARCHAR(120) NOT NULL UNIQUE,
  description TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS role_permissions (
  role_id UUID NOT NULL REFERENCES roles(id),
  permission_id UUID NOT NULL REFERENCES permissions(id),
  PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE IF NOT EXISTS user_roles (
  user_id UUID NOT NULL REFERENCES users(id),
  organization_id UUID NOT NULL REFERENCES organizations(id),
  role_id UUID NOT NULL REFERENCES roles(id),
  PRIMARY KEY (user_id, organization_id, role_id)
);

CREATE TABLE IF NOT EXISTS sessions (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id),
  token_hash VARCHAR(128) NOT NULL UNIQUE,
  expires_at TIMESTAMPTZ NOT NULL,
  revoked_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  ip_address INET,
  user_agent TEXT
);

CREATE TABLE IF NOT EXISTS audit_logs (
  id UUID PRIMARY KEY,
  organization_id UUID REFERENCES organizations(id),
  actor_user_id UUID REFERENCES users(id),
  action VARCHAR(120) NOT NULL,
  resource_type VARCHAR(120) NOT NULL,
  resource_id UUID,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_memberships_organization ON organization_memberships(organization_id, status);
CREATE INDEX IF NOT EXISTS idx_memberships_user ON organization_memberships(user_id, status);
CREATE INDEX IF NOT EXISTS idx_divisions_organization ON divisions(organization_id);
CREATE INDEX IF NOT EXISTS idx_departments_division ON departments(division_id);
CREATE INDEX IF NOT EXISTS idx_teams_department ON teams(department_id);
CREATE INDEX IF NOT EXISTS idx_assignments_user_org ON user_organizational_assignments(user_id, organization_id, is_primary);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id, expires_at);
CREATE INDEX IF NOT EXISTS idx_sessions_active ON sessions(token_hash, expires_at) WHERE revoked_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_audit_logs_org_time ON audit_logs(organization_id, created_at DESC);

INSERT INTO roles (id, code, description) VALUES
  (gen_random_uuid(), 'ORG_ADMIN', 'Organization-wide administration'),
  (gen_random_uuid(), 'DIVISION_MANAGER', 'Management within an assigned division'),
  (gen_random_uuid(), 'DEPARTMENT_MANAGER', 'Management within an assigned department'),
  (gen_random_uuid(), 'TEAM_LEAD', 'Management within an assigned team'),
  (gen_random_uuid(), 'EMPLOYEE', 'Standard organization membership')
ON CONFLICT (code) DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
CROSS JOIN permissions p
WHERE r.code = 'ORG_ADMIN'
ON CONFLICT DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
JOIN permissions p ON p.code IN (
  'user.read', 'organization.read', 'organization.members.read',
  'division.read', 'division.manage', 'department.read', 'department.manage',
  'team.read', 'team.manage', 'meeting.read', 'meeting.create',
  'meeting.update', 'meeting.join', 'meeting.manage_participants',
  'document.read', 'document.create', 'document.update',
  'artifact.read', 'artifact.create'
)
WHERE r.code = 'DIVISION_MANAGER'
ON CONFLICT DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
JOIN permissions p ON p.code IN (
  'user.read', 'organization.read', 'organization.members.read',
  'department.read', 'department.manage', 'team.read', 'team.manage',
  'meeting.read', 'meeting.create', 'meeting.update', 'meeting.join',
  'meeting.manage_participants', 'document.read', 'document.create',
  'document.update', 'artifact.read', 'artifact.create'
)
WHERE r.code = 'DEPARTMENT_MANAGER'
ON CONFLICT DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
JOIN permissions p ON p.code IN (
  'user.read', 'organization.read', 'organization.members.read',
  'team.read', 'team.manage', 'meeting.read', 'meeting.create',
  'meeting.join', 'meeting.manage_participants', 'document.read',
  'document.create', 'artifact.read', 'artifact.create'
)
WHERE r.code = 'TEAM_LEAD'
ON CONFLICT DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
JOIN permissions p ON p.code IN (
  'organization.read', 'organization.members.read', 'team.read',
  'meeting.read', 'meeting.join', 'document.read', 'artifact.read'
)
WHERE r.code = 'EMPLOYEE'
ON CONFLICT DO NOTHING;

INSERT INTO permissions (id, code, description) VALUES
  (gen_random_uuid(), 'user.read', 'View permitted application users'),
  (gen_random_uuid(), 'user.create', 'Provision users into an organization'),
  (gen_random_uuid(), 'user.update', 'Update permitted user records'),
  (gen_random_uuid(), 'user.disable', 'Suspend or disable permitted users'),
  (gen_random_uuid(), 'organization.read', 'View organization information'),
  (gen_random_uuid(), 'organization.update', 'Update organization settings'),
  (gen_random_uuid(), 'organization.members.read', 'View organization membership'),
  (gen_random_uuid(), 'organization.members.manage', 'Manage organization membership'),
  (gen_random_uuid(), 'division.read', 'View permitted divisions'),
  (gen_random_uuid(), 'division.manage', 'Manage permitted divisions'),
  (gen_random_uuid(), 'department.read', 'View permitted departments'),
  (gen_random_uuid(), 'department.manage', 'Manage permitted departments'),
  (gen_random_uuid(), 'team.read', 'View permitted teams'),
  (gen_random_uuid(), 'team.manage', 'Manage permitted teams'),
  (gen_random_uuid(), 'meeting.read', 'View permitted meetings'),
  (gen_random_uuid(), 'meeting.create', 'Create permitted meetings'),
  (gen_random_uuid(), 'meeting.update', 'Update permitted meetings'),
  (gen_random_uuid(), 'meeting.delete', 'Delete permitted meetings'),
  (gen_random_uuid(), 'meeting.join', 'Join permitted meetings'),
  (gen_random_uuid(), 'meeting.manage_participants', 'Manage meeting participants'),
  (gen_random_uuid(), 'chat.read', 'Read permitted conversations'),
  (gen_random_uuid(), 'chat.create', 'Create permitted messages'),
  (gen_random_uuid(), 'chat.delete', 'Delete permitted messages'),
  (gen_random_uuid(), 'document.read', 'Read permitted documents'),
  (gen_random_uuid(), 'document.create', 'Create permitted documents'),
  (gen_random_uuid(), 'document.update', 'Update permitted documents'),
  (gen_random_uuid(), 'document.delete', 'Delete permitted documents'),
  (gen_random_uuid(), 'artifact.read', 'Read permitted artifacts'),
  (gen_random_uuid(), 'artifact.create', 'Create permitted artifacts'),
  (gen_random_uuid(), 'admin.audit.read', 'View organization audit information')
ON CONFLICT (code) DO NOTHING;
