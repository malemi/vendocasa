/**
 * Supabase Auth client: email sign-in links and session refresh.
 *
 * VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY (the project's public client
 * key) are read at build time. Without them sign-in is unavailable and the
 * chat stays closed; the backend refuses every API call without a session.
 */

import { createClient, type SupabaseClient } from "@supabase/supabase-js";

const url = import.meta.env.VITE_SUPABASE_URL as string | undefined;
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined;

export const supabase: SupabaseClient | null =
  url && anonKey
    ? createClient(url, anonKey, {
        auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true },
      })
    : null;

/** The current access token, refreshed by the client when it nears expiry. */
export async function accessToken(): Promise<string | null> {
  if (!supabase) return null;
  const { data } = await supabase.auth.getSession();
  return data.session?.access_token ?? null;
}
