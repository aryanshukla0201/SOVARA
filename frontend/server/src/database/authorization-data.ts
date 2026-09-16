import { databasePool, requireDatabase } from "./pool.js";

export type RolePermissionIds = {
  roleIds: string[];
  permissionIds: string[];
};

export async function rolePermissionIds(roleCode: string): Promise<RolePermissionIds> {
  const result = await (databasePool ?? requireDatabase()).query<{
    role_id: string;
    permission_id: string | null;
  }>(
    `SELECT role.id AS role_id, permission.id AS permission_id
     FROM roles role
     LEFT JOIN role_permissions mapping ON mapping.role_id = role.id
     LEFT JOIN permissions permission ON permission.id = mapping.permission_id
     WHERE role.code = $1`,
    [roleCode],
  );
  const roleId = result.rows[0]?.role_id;
  return {
    roleIds: roleId ? [roleId] : [],
    permissionIds: result.rows
      .map((row) => row.permission_id)
      .filter((permissionId): permissionId is string => Boolean(permissionId)),
  };
}
