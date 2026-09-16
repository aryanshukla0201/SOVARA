CREATE INDEX IF NOT EXISTS idx_memberships_active_organization
  ON organization_memberships(organization_id, user_id)
  WHERE status = 'ACTIVE';

CREATE INDEX IF NOT EXISTS idx_memberships_active_user
  ON organization_memberships(user_id, organization_id)
  WHERE status = 'ACTIVE';

ALTER TABLE organization_memberships
  DROP CONSTRAINT IF EXISTS organization_memberships_left_at_check;

ALTER TABLE organization_memberships
  ADD CONSTRAINT organization_memberships_left_at_check
  CHECK ((status = 'LEFT') = (left_at IS NOT NULL));
