ALTER TABLE divisions
  DROP CONSTRAINT IF EXISTS divisions_id_organization_key;
ALTER TABLE divisions
  ADD CONSTRAINT divisions_id_organization_key UNIQUE (id, organization_id);

ALTER TABLE departments
  DROP CONSTRAINT IF EXISTS departments_id_division_key;
ALTER TABLE departments
  ADD CONSTRAINT departments_id_division_key UNIQUE (id, division_id);

ALTER TABLE teams
  DROP CONSTRAINT IF EXISTS teams_id_department_key;
ALTER TABLE teams
  ADD CONSTRAINT teams_id_department_key UNIQUE (id, department_id);

DO $$
DECLARE
  old_constraint text;
BEGIN
  SELECT conname INTO old_constraint
  FROM pg_constraint
  WHERE conrelid = 'user_organizational_assignments'::regclass
    AND contype = 'u'
    AND pg_get_constraintdef(oid) = 'UNIQUE (user_id, organization_id, is_primary)';

  IF old_constraint IS NOT NULL THEN
    EXECUTE format(
      'ALTER TABLE user_organizational_assignments DROP CONSTRAINT %I',
      old_constraint
    );
  END IF;
END;
$$;

ALTER TABLE user_organizational_assignments
  DROP CONSTRAINT IF EXISTS user_assignments_department_requires_division;
ALTER TABLE user_organizational_assignments
  ADD CONSTRAINT user_assignments_department_requires_division
  CHECK (department_id IS NULL OR division_id IS NOT NULL);

ALTER TABLE user_organizational_assignments
  DROP CONSTRAINT IF EXISTS user_assignments_team_requires_department;
ALTER TABLE user_organizational_assignments
  ADD CONSTRAINT user_assignments_team_requires_department
  CHECK (team_id IS NULL OR department_id IS NOT NULL);

ALTER TABLE user_organizational_assignments
  DROP CONSTRAINT IF EXISTS user_assignments_manager_not_self;
ALTER TABLE user_organizational_assignments
  ADD CONSTRAINT user_assignments_manager_not_self
  CHECK (manager_user_id IS NULL OR manager_user_id <> user_id);

ALTER TABLE user_organizational_assignments
  DROP CONSTRAINT IF EXISTS user_assignments_division_organization_fkey;
ALTER TABLE user_organizational_assignments
  ADD CONSTRAINT user_assignments_division_organization_fkey
  FOREIGN KEY (division_id, organization_id)
  REFERENCES divisions (id, organization_id);

ALTER TABLE user_organizational_assignments
  DROP CONSTRAINT IF EXISTS user_assignments_department_division_fkey;
ALTER TABLE user_organizational_assignments
  ADD CONSTRAINT user_assignments_department_division_fkey
  FOREIGN KEY (department_id, division_id)
  REFERENCES departments (id, division_id);

ALTER TABLE user_organizational_assignments
  DROP CONSTRAINT IF EXISTS user_assignments_team_department_fkey;
ALTER TABLE user_organizational_assignments
  ADD CONSTRAINT user_assignments_team_department_fkey
  FOREIGN KEY (team_id, department_id)
  REFERENCES teams (id, department_id);

CREATE UNIQUE INDEX IF NOT EXISTS idx_one_primary_assignment_per_user_org
  ON user_organizational_assignments(user_id, organization_id)
  WHERE is_primary;

CREATE INDEX IF NOT EXISTS idx_assignments_user_history
  ON user_organizational_assignments(user_id, organization_id, valid_from DESC);

CREATE INDEX IF NOT EXISTS idx_assignments_manager
  ON user_organizational_assignments(manager_user_id, organization_id)
  WHERE manager_user_id IS NOT NULL;
