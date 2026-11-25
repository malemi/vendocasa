/**
 * Turn an API refusal into the Italian message shown to the user.
 *
 * The backend refuses with `{"detail": {"error": <code>, "message": <Italian>}}`
 * (backend/app/refusals.py). Some older validation errors still send
 * `{"detail": "<Italian text>"}`. Anything else gets a generic message, so the
 * user never sees raw JSON or English provider text.
 */

export const GENERIC_ERROR = "Si è verificato un problema. Riprova tra poco.";
export const NETWORK_ERROR =
  "Impossibile raggiungere VendoCasa. Controlla la connessione e riprova.";

/** Codes after which the user must sign in again. */
export const SIGN_IN_AGAIN_CODES = new Set([
  "not_authenticated",
  "session_expired",
  "invalid_token",
]);

export interface Refusal {
  code: string | null;
  message: string;
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string | null;

  constructor(refusal: Refusal, status: number) {
    super(refusal.message);
    this.name = "ApiError";
    this.status = status;
    this.code = refusal.code;
  }

  get requiresSignIn(): boolean {
    return this.code !== null && SIGN_IN_AGAIN_CODES.has(this.code);
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** Extract the user-facing refusal from a parsed response body. */
export function refusalFromBody(body: unknown): Refusal {
  const detail = isRecord(body) ? body.detail : undefined;
  if (isRecord(detail)) {
    const code = typeof detail.error === "string" ? detail.error : null;
    const message =
      typeof detail.message === "string" && detail.message.trim()
        ? detail.message
        : GENERIC_ERROR;
    return { code, message };
  }
  if (typeof detail === "string" && detail.trim()) {
    return { code: null, message: detail };
  }
  return { code: null, message: GENERIC_ERROR };
}

/** Build an ApiError from a non-OK fetch Response. */
export async function apiErrorFromResponse(response: Response): Promise<ApiError> {
  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    body = null;
  }
  return new ApiError(refusalFromBody(body), response.status);
}

/** The message to show for any error thrown by an API call. */
export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof TypeError) return NETWORK_ERROR; // fetch network failure
  return GENERIC_ERROR;
}
