CREATE INDEX IF NOT EXISTS idx_organizations_status ON organizations(status);

CREATE OR REPLACE FUNCTION set_organizations_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS organizations_set_updated_at ON organizations;

CREATE TRIGGER organizations_set_updated_at
BEFORE UPDATE ON organizations
FOR EACH ROW
EXECUTE FUNCTION set_organizations_updated_at();
