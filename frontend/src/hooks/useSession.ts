import { useEffect, useState } from "react";
import type { Session } from "@supabase/supabase-js";
import { supabase } from "../auth/supabase";

// A sign-in link returns to the site with the session in the URL fragment.
const arrivedFromSignInLink =
  typeof window !== "undefined" && window.location.hash.includes("access_token=");

export interface SessionState {
  session: Session | null;
  /** False until the stored session (if any) has been read. */
  ready: boolean;
  /** True when this page load came from a sign-in link. */
  arrivedFromSignInLink: boolean;
}

export function useSession(): SessionState {
  const [session, setSession] = useState<Session | null>(null);
  const [ready, setReady] = useState(supabase === null);

  useEffect(() => {
    if (!supabase) return;
    let active = true;
    supabase.auth.getSession().then(({ data }) => {
      if (!active) return;
      setSession(data.session);
      setReady(true);
    });
    const { data } = supabase.auth.onAuthStateChange((_event, next) => {
      setSession(next);
      setReady(true);
    });
    return () => {
      active = false;
      data.subscription.unsubscribe();
    };
  }, []);

  return { session, ready, arrivedFromSignInLink };
}

/** Sign out on this device only; sessions on the user's other devices stay valid. */
export async function signOut(): Promise<void> {
  if (supabase) await supabase.auth.signOut({ scope: "local" });
}
