import "dotenv/config";
import { readdir, readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { requireDatabase } from "./pool.js";

const migrationsDirectory = join(dirname(fileURLToPath(import.meta.url)), "../../migrations");
const pool = requireDatabase();

try {
  await pool.query(`
    CREATE TABLE IF NOT EXISTS schema_migrations (
      version VARCHAR(255) PRIMARY KEY,
      applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
  `);
  const files = (await readdir(migrationsDirectory))
    .filter((file) => /^\d+_[a-z0-9_-]+\.sql$/i.test(file))
    .sort();
  for (const file of files) {
    const alreadyApplied = await pool.query("SELECT 1 FROM schema_migrations WHERE version = $1", [file]);
    if (alreadyApplied.rowCount) continue;
    const migration = await readFile(join(migrationsDirectory, file), "utf8");
    await pool.query("BEGIN");
    try {
      await pool.query(migration);
      await pool.query("INSERT INTO schema_migrations (version) VALUES ($1)", [file]);
      await pool.query("COMMIT");
      console.log(`[db] applied ${file}`);
    } catch (error) {
      await pool.query("ROLLBACK");
      throw error;
    }
  }
} finally {
  await pool.end();
}
