/** Italian messages for sign-in link requests refused by Supabase Auth. */

export interface AuthErrorLike {
  status?: number;
  code?: string;
  message?: string;
}

export const SIGN_IN_RATE_LIMITED = "Troppe richieste di accesso. Riprova tra qualche minuto.";
export const SIGN_IN_BAD_ADDRESS = "Controlla l'indirizzo email e riprova.";
export const SIGN_IN_FAILED = "Non è stato possibile inviare il link. Riprova tra poco.";
export const SIGN_IN_UNAVAILABLE = "L'accesso non è disponibile in questo momento. Riprova più tardi.";

// The before-user-created hook (backend migration 0003) refuses disposable
// addresses with this Italian message, which Supabase passes through.
const DISPOSABLE_REFUSAL = "Questo indirizzo email non è accettato. Usa un indirizzo personale.";

export function signInErrorMessage(error: AuthErrorLike): string {
  if (error.message?.includes(DISPOSABLE_REFUSAL)) return DISPOSABLE_REFUSAL;
  if (error.status === 429 || error.code === "over_email_send_rate_limit") return SIGN_IN_RATE_LIMITED;
  if (error.code === "email_address_invalid" || error.code === "validation_failed") return SIGN_IN_BAD_ADDRESS;
  return SIGN_IN_FAILED;
}
