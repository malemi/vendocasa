/**
 * The local stack the journeys run against: local Supabase (supabase/config.toml),
 * the backend from backend/tests/e2e/serve.py and the built frontend.
 *
 * E2E_SUPABASE_STATUS_ENV names the file that `npx supabase@3.4.0 status -o env`
 * printed for the stack. Its keys are the stack's own development keys.
 *
 * External mode: when E2E_APP_URL is set, the journeys start no servers and
 * drive an already running deployment, such as the server rehearsal
 * (deploy/compose.rehearsal.yaml), where the app and its API share that one
 * origin. The status file then comes from deploy/make_secrets.py: its API_URL is the
 * address of Auth's admin calls, and MAILPIT_URL the rehearsal's mail catcher.
 */

import { readFileSync } from "node:fs";

export const EXTERNAL_APP_URL = process.env.E2E_APP_URL || undefined;
export const API_URL = EXTERNAL_APP_URL ?? "http://127.0.0.1:8000";
export const APP_URL = EXTERNAL_APP_URL ?? "http://127.0.0.1:4173";
export const OWNER_EMAIL = "owner@vendocasa.test";

/** Micro-dollars one substitute model call costs (backend/tests/e2e/substitute.py). */
export const MICRO_USD_PER_CALL = 4_500;

export type StackStatus = Record<string, string>;

export function loadStatus(path = process.env.E2E_SUPABASE_STATUS_ENV): StackStatus {
  if (!path) {
    throw new Error("Set E2E_SUPABASE_STATUS_ENV to the file printed by `npx supabase@3.4.0 status -o env`.");
  }
  const values: StackStatus = {};
  for (const line of readFileSync(path, "utf8").split("\n")) {
    const at = line.indexOf("=");
    if (at > 0) values[line.slice(0, at).trim()] = line.slice(at + 1).trim().replace(/^"|"$/g, "");
  }
  for (const key of ["API_URL", "ANON_KEY", "SERVICE_ROLE_KEY", "MAILPIT_URL"]) {
    if (!values[key]) throw new Error(`${key} is missing from ${path}`);
  }
  return values;
}

/** An access token for an existing account, without sending any email. */
export async function sessionFor(status: StackStatus, email: string): Promise<string> {
  const admin = { apikey: status.SERVICE_ROLE_KEY, Authorization: `Bearer ${status.SERVICE_ROLE_KEY}` };
  const link = await fetch(`${status.API_URL}/auth/v1/admin/generate_link`, {
    method: "POST",
    headers: { ...admin, "content-type": "application/json" },
    body: JSON.stringify({ type: "magiclink", email }),
  });
  if (link.status !== 200) throw new Error(`generate_link for ${email}: ${link.status}`);
  const { hashed_token } = (await link.json()) as { hashed_token: string };
  const verify = await fetch(`${status.API_URL}/auth/v1/verify`, {
    method: "POST",
    headers: { apikey: status.ANON_KEY, "content-type": "application/json" },
    body: JSON.stringify({ type: "magiclink", token_hash: hashed_token }),
  });
  if (verify.status !== 200) throw new Error(`verify for ${email}: ${verify.status}`);
  return ((await verify.json()) as { access_token: string }).access_token;
}

/** The sign-in link in the latest message the local mail catcher holds for `email`. */
export async function signInLinkFor(status: StackStatus, email: string): Promise<string> {
  const query = encodeURIComponent(`to:"${email}"`);
  for (let attempt = 0; attempt < 20; attempt++) {
    const search = await fetch(`${status.MAILPIT_URL}/api/v1/search?query=${query}`);
    const { messages } = (await search.json()) as { messages: Array<{ ID: string }> };
    if (messages.length > 0) {
      const message = await fetch(`${status.MAILPIT_URL}/api/v1/message/${messages[0].ID}`);
      const { HTML } = (await message.json()) as { HTML: string };
      const href = HTML.match(/href="([^"]*\/auth\/v1\/verify[^"]*)"/)?.[1];
      if (!href) throw new Error(`No sign-in link in the message to ${email}`);
      return href.replaceAll("&amp;", "&");
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error(`No message for ${email} in the mail catcher`);
}

export async function api(path: string, token: string, init: RequestInit = {}): Promise<Response> {
  return fetch(`${API_URL}${path}`, {
    ...init,
    headers: { ...(init.headers ?? {}), Authorization: `Bearer ${token}`, "content-type": "application/json" },
  });
}
