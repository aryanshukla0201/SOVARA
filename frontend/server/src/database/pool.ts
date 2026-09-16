import { Pool } from "pg";

const databaseUrl = process.env.DATABASE_URL?.trim();

export const databaseConfigured = Boolean(databaseUrl);
export const databasePool = databaseUrl
  ? new Pool({ connectionString: databaseUrl, max: Number(process.env.DB_POOL_MAX ?? 10) })
  : null;

export function requireDatabase(): Pool {
  if (!databasePool) throw new Error("DATABASE_URL is required for database migrations");
  return databasePool;
}
