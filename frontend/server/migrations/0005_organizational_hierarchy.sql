CREATE INDEX IF NOT EXISTS idx_divisions_organization_code
  ON divisions(organization_id, code);

CREATE INDEX IF NOT EXISTS idx_departments_division_code
  ON departments(division_id, code);

CREATE INDEX IF NOT EXISTS idx_teams_department_code
  ON teams(department_id, code);

ALTER TABLE divisions DROP CONSTRAINT IF EXISTS divisions_name_check;
ALTER TABLE divisions ADD CONSTRAINT divisions_name_check CHECK (btrim(name) <> '');
ALTER TABLE divisions DROP CONSTRAINT IF EXISTS divisions_code_check;
ALTER TABLE divisions ADD CONSTRAINT divisions_code_check CHECK (code = upper(code) AND btrim(code) <> '');

ALTER TABLE departments DROP CONSTRAINT IF EXISTS departments_name_check;
ALTER TABLE departments ADD CONSTRAINT departments_name_check CHECK (btrim(name) <> '');
ALTER TABLE departments DROP CONSTRAINT IF EXISTS departments_code_check;
ALTER TABLE departments ADD CONSTRAINT departments_code_check CHECK (code = upper(code) AND btrim(code) <> '');

ALTER TABLE teams DROP CONSTRAINT IF EXISTS teams_name_check;
ALTER TABLE teams ADD CONSTRAINT teams_name_check CHECK (btrim(name) <> '');
ALTER TABLE teams DROP CONSTRAINT IF EXISTS teams_code_check;
ALTER TABLE teams ADD CONSTRAINT teams_code_check CHECK (code = upper(code) AND btrim(code) <> '');

CREATE OR REPLACE FUNCTION set_hierarchy_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS divisions_set_updated_at ON divisions;
CREATE TRIGGER divisions_set_updated_at
BEFORE UPDATE ON divisions
FOR EACH ROW EXECUTE FUNCTION set_hierarchy_updated_at();

DROP TRIGGER IF EXISTS departments_set_updated_at ON departments;
CREATE TRIGGER departments_set_updated_at
BEFORE UPDATE ON departments
FOR EACH ROW EXECUTE FUNCTION set_hierarchy_updated_at();

DROP TRIGGER IF EXISTS teams_set_updated_at ON teams;
CREATE TRIGGER teams_set_updated_at
BEFORE UPDATE ON teams
FOR EACH ROW EXECUTE FUNCTION set_hierarchy_updated_at();
