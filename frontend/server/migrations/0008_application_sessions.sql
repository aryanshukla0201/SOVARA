CREATE INDEX IF NOT EXISTS idx_sessions_expiry ON sessions(expires_at);

CREATE INDEX IF NOT EXISTS idx_sessions_revoked ON sessions(revoked_at)
  WHERE revoked_at IS NOT NULL;
