const required = (name: string, fallback?: string): string => {
  const value = process.env[name]?.trim() || fallback;
  if (!value) throw new Error(`Missing required environment variable: ${name}`);
  return value;
};

const booleanEnv = (name: string, fallback: boolean): boolean => {
  const value = process.env[name]?.trim().toLowerCase();
  if (!value) return fallback;
  return value === "true";
};

export const authConfig = {
  issuer: required(
    "KEYCLOAK_ISSUER",
    "http://localhost:8081/realms/sovara-local",
  ).replace(/\/+$/, ""),
  clientId: required("KEYCLOAK_CLIENT_ID", "sovara-backend-local"),
  clientSecret: process.env.KEYCLOAK_CLIENT_SECRET?.trim(),
  redirectUri: required(
    "KEYCLOAK_REDIRECT_URI",
    "http://localhost:3000/api/auth/callback/keycloak",
  ),
  postLogoutRedirectUri: required(
    "KEYCLOAK_POST_LOGOUT_REDIRECT_URI",
    "http://localhost:8080/",
  ),
  frontendOrigin: required("FRONTEND_ORIGIN", "http://localhost:8080"),
  sessionCookieSecure: booleanEnv("SESSION_COOKIE_SECURE", true),
  sessionTtlMs: 8 * 60 * 60 * 1000,
  loginTransactionTtlMs: 5 * 60 * 1000,
};

export function isSafeReturnTo(value: string): boolean {
  return value.startsWith("/") && !value.startsWith("//") && !value.includes("\\");
}
