import { randomUUID } from "node:crypto";
import type { Pool, QueryResultRow } from "pg";
import { databasePool, requireDatabase } from "./pool.js";
import type { DepartmentRecord, DivisionRecord, TeamRecord } from "./models.js";

export type HierarchyNodeInput = {
  name: string;
  code: string;
};

type DivisionRow = QueryResultRow & {
  id: string;
  organization_id: string;
  name: string;
  code: string;
  created_at: Date;
  updated_at: Date;
};

type DepartmentRow = QueryResultRow & {
  id: string;
  division_id: string;
  name: string;
  code: string;
  created_at: Date;
  updated_at: Date;
};

type TeamRow = QueryResultRow & {
  id: string;
  department_id: string;
  name: string;
  code: string;
  created_at: Date;
  updated_at: Date;
};

function required(value: string, field: string): string {
  const normalized = value.trim();
  if (!normalized) throw new Error(`${field} is required`);
  return normalized;
}

function code(value: string): string {
  return required(value, "code").toUpperCase();
}

function divisionFromRow(row: DivisionRow): DivisionRecord {
  return {
    id: row.id,
    organizationId: row.organization_id,
    name: row.name,
    code: row.code,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

function departmentFromRow(row: DepartmentRow): DepartmentRecord {
  return {
    id: row.id,
    divisionId: row.division_id,
    name: row.name,
    code: row.code,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

function teamFromRow(row: TeamRow): TeamRecord {
  return {
    id: row.id,
    departmentId: row.department_id,
    name: row.name,
    code: row.code,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

const divisionColumns = "id, organization_id, name, code, created_at, updated_at";
const departmentColumns = "id, division_id, name, code, created_at, updated_at";
const teamColumns = "id, department_id, name, code, created_at, updated_at";

export class HierarchyRepository {
  constructor(private readonly pool: Pool = requireDatabase()) {}

  async createDivision(organizationId: string, input: HierarchyNodeInput): Promise<DivisionRecord> {
    const result = await this.pool.query<DivisionRow>(
      `INSERT INTO divisions (id, organization_id, name, code)
       VALUES ($1, $2, $3, $4)
       RETURNING ${divisionColumns}`,
      [randomUUID(), required(organizationId, "organizationId"), required(input.name, "name"), code(input.code)],
    );
    const row = result.rows[0];
    if (!row) throw new Error("Division insert returned no row");
    return divisionFromRow(row);
  }

  async listDivisions(organizationId: string): Promise<DivisionRecord[]> {
    const result = await this.pool.query<DivisionRow>(
      `SELECT ${divisionColumns} FROM divisions
       WHERE organization_id = $1 ORDER BY code ASC`,
      [required(organizationId, "organizationId")],
    );
    return result.rows.map(divisionFromRow);
  }

  async createDepartment(divisionId: string, input: HierarchyNodeInput): Promise<DepartmentRecord> {
    const result = await this.pool.query<DepartmentRow>(
      `INSERT INTO departments (id, division_id, name, code)
       VALUES ($1, $2, $3, $4)
       RETURNING ${departmentColumns}`,
      [randomUUID(), required(divisionId, "divisionId"), required(input.name, "name"), code(input.code)],
    );
    const row = result.rows[0];
    if (!row) throw new Error("Department insert returned no row");
    return departmentFromRow(row);
  }

  async listDepartments(divisionId: string): Promise<DepartmentRecord[]> {
    const result = await this.pool.query<DepartmentRow>(
      `SELECT ${departmentColumns} FROM departments
       WHERE division_id = $1 ORDER BY code ASC`,
      [required(divisionId, "divisionId")],
    );
    return result.rows.map(departmentFromRow);
  }

  async createTeam(departmentId: string, input: HierarchyNodeInput): Promise<TeamRecord> {
    const result = await this.pool.query<TeamRow>(
      `INSERT INTO teams (id, department_id, name, code)
       VALUES ($1, $2, $3, $4)
       RETURNING ${teamColumns}`,
      [randomUUID(), required(departmentId, "departmentId"), required(input.name, "name"), code(input.code)],
    );
    const row = result.rows[0];
    if (!row) throw new Error("Team insert returned no row");
    return teamFromRow(row);
  }

  async listTeams(departmentId: string): Promise<TeamRecord[]> {
    const result = await this.pool.query<TeamRow>(
      `SELECT ${teamColumns} FROM teams
       WHERE department_id = $1 ORDER BY code ASC`,
      [required(departmentId, "departmentId")],
    );
    return result.rows.map(teamFromRow);
  }
}

export function hierarchyRepository(): HierarchyRepository {
  return new HierarchyRepository(databasePool ?? requireDatabase());
}
