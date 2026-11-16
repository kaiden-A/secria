import { cookies } from "next/headers";

import { SESSION_COOKIE } from "@/lib/session-cookie";

const API_ORIGIN = process.env.API_ORIGIN ?? "http://localhost:8000";

/**
 * True when the browser's session cookie still resolves to a user.
 *
 * Server-only: `cookies()` is unavailable in Client Components. A network or
 * API failure returns false so the caller can fall back to the signed-out path
 * instead of locking people out.
 */
export async function hasValidSession(): Promise<boolean> {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) return false;

  try {
    const response = await fetch(`${API_ORIGIN.replace(/\/$/, "")}/api/v1/me`, {
      headers: { cookie: `${SESSION_COOKIE}=${token}` },
      cache: "no-store",
      signal: AbortSignal.timeout(3_000),
    });
    return response.ok;
  } catch {
    return false;
  }
}
