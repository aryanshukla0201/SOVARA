ALTER TABLE user_organizational_assignments
  DROP CONSTRAINT IF EXISTS user_assignments_user_membership_fkey;
ALTER TABLE user_organizational_assignments
  ADD CONSTRAINT user_assignments_user_membership_fkey
  FOREIGN KEY (user_id, organization_id)
  REFERENCES organization_memberships (user_id, organization_id);

ALTER TABLE user_organizational_assignments
  DROP CONSTRAINT IF EXISTS user_assignments_manager_membership_fkey;
ALTER TABLE user_organizational_assignments
  ADD CONSTRAINT user_assignments_manager_membership_fkey
  FOREIGN KEY (manager_user_id, organization_id)
  REFERENCES organization_memberships (user_id, organization_id);

CREATE INDEX IF NOT EXISTS idx_primary_assignment_department
  ON user_organizational_assignments(organization_id, department_id, user_id)
  WHERE is_primary AND valid_until IS NULL;

CREATE INDEX IF NOT EXISTS idx_primary_assignment_team
  ON user_organizational_assignments(organization_id, team_id, user_id)
  WHERE is_primary AND valid_until IS NULL;
