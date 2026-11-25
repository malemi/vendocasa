/**
 * Sign-in with an emailed link (Supabase Auth). New addresses are registered
 * by the same link; there is no password.
 */

import { useState } from "react";
import { supabase } from "../../auth/supabase";
import { SIGN_IN_UNAVAILABLE, signInErrorMessage } from "../../auth/signInErrors";
import { Button } from "../ui/Button";

interface SignInPanelProps {
  /** Why the user is asked to sign in again (for example, an expired session). */
  notice?: string | null;
}

type Step = "form" | "sending" | "sent";

export function SignInPanel({ notice }: SignInPanelProps) {
  const [email, setEmail] = useState("");
  const [step, setStep] = useState<Step>("form");
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!supabase) {
      setError(SIGN_IN_UNAVAILABLE);
      return;
    }
    setError(null);
    setStep("sending");
    const { error: authError } = await supabase.auth.signInWithOtp({
      email: email.trim(),
      options: { emailRedirectTo: window.location.origin, shouldCreateUser: true },
    });
    if (authError) {
      setStep("form");
      setError(signInErrorMessage(authError));
      return;
    }
    setStep("sent");
  };

  return (
    <div className="flex-1 flex flex-col items-center justify-center px-6 py-10 text-center">
      <div className="w-full max-w-sm">
        <h2 className="text-xl font-semibold text-text-primary mb-2">Accedi a VendoCasa</h2>
        {notice && (
          <p className="text-sm text-text-secondary mb-4" role="status">
            {notice}
          </p>
        )}

        {step === "sent" ? (
          <div role="status">
            <p className="text-text-secondary">
              Ti abbiamo inviato un link a <strong className="text-text-primary">{email.trim()}</strong>.
            </p>
            <p className="text-text-secondary mt-2">Aprilo per entrare. Il link vale una sola volta.</p>
            <button
              type="button"
              className="mt-6 text-sm text-accent hover:underline cursor-pointer"
              onClick={() => setStep("form")}
            >
              Usa un altro indirizzo
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="flex flex-col gap-3 text-left">
            <p className="text-sm text-text-secondary text-center mb-2">
              Gratis. Inserisci la tua email e ti mandiamo un link per entrare, senza password.
            </p>
            <label htmlFor="signin-email" className="text-sm text-text-secondary">
              Email
            </label>
            <input
              id="signin-email"
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-lg border border-border bg-bg-surface px-3 py-2 text-text-primary"
              placeholder="nome@esempio.it"
            />
            {error && (
              <p className="text-sm text-danger" role="alert">
                {error}
              </p>
            )}
            <Button type="submit" disabled={step === "sending" || !email.trim()}>
              {step === "sending" ? "Invio in corso..." : "Inviami il link"}
            </Button>
          </form>
        )}
      </div>
    </div>
  );
}
