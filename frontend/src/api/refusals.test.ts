import { describe, expect, it } from "vitest";
import {
  ApiError,
  GENERIC_ERROR,
  NETWORK_ERROR,
  apiErrorFromResponse,
  errorMessage,
  refusalFromBody,
} from "./refusals";

// One representative body per refusal the brief lists (scope 1), as the
// backend sends it (backend/app/refusals.py).
const REFUSALS: Array<[string, string]> = [
  ["not_authenticated", "Accedi con la tua email per usare VendoCasa."],
  ["account_limit", "Hai usato tutto il credito gratuito di questo mese."],
  ["global_limit", "VendoCasa ha esaurito il credito gratuito disponibile per questo mese."],
  ["daily_limit", "VendoCasa ha raggiunto il limite di richieste di oggi. Riprova domani."],
  ["paused", "L'assistente è momentaneamente in pausa. Riprova più tardi."],
  ["rate_limited", "Troppe richieste ravvicinate. Attendi qualche istante e riprova."],
  ["too_large", "Il file o la richiesta è troppo grande."],
  ["concurrent", "C'è già una risposta in corso. Attendi che finisca."],
];

describe("refusalFromBody", () => {
  it.each(REFUSALS)("shows the Italian message for %s", (code, message) => {
    expect(refusalFromBody({ detail: { error: code, message } })).toEqual({ code, message });
  });

  it("shows a plain string detail as is", () => {
    expect(refusalFromBody({ detail: "Messaggio troppo lungo (massimo 4000 caratteri)." })).toEqual({
      code: null,
      message: "Messaggio troppo lungo (massimo 4000 caratteri).",
    });
  });

  it("never shows raw validation errors or unknown bodies", () => {
    expect(refusalFromBody({ detail: [{ loc: ["body"], msg: "field required" }] }).message).toBe(
      GENERIC_ERROR,
    );
    expect(refusalFromBody({ detail: { error: "x" } }).message).toBe(GENERIC_ERROR);
    expect(refusalFromBody("<html>502</html>").message).toBe(GENERIC_ERROR);
    expect(refusalFromBody(null).message).toBe(GENERIC_ERROR);
  });
});

describe("ApiError", () => {
  it("asks to sign in again only for session problems", () => {
    const expired = new ApiError({ code: "session_expired", message: "x" }, 401);
    const limited = new ApiError({ code: "rate_limited", message: "x" }, 429);
    expect(expired.requiresSignIn).toBe(true);
    expect(limited.requiresSignIn).toBe(false);
  });

  it("is built from a fetch response, including a non-JSON one", async () => {
    const json = new Response(
      JSON.stringify({ detail: { error: "rate_limited", message: "Troppe richieste ravvicinate." } }),
      { status: 429 },
    );
    const error = await apiErrorFromResponse(json);
    expect([error.status, error.code, error.message]).toEqual([429, "rate_limited", "Troppe richieste ravvicinate."]);

    const html = await apiErrorFromResponse(new Response("<html>bad gateway</html>", { status: 502 }));
    expect(html.message).toBe(GENERIC_ERROR);
  });

  it("maps network failures and unknown errors to Italian messages", () => {
    expect(errorMessage(new TypeError("Failed to fetch"))).toBe(NETWORK_ERROR);
    expect(errorMessage(new Error("boom"))).toBe(GENERIC_ERROR);
  });
});
