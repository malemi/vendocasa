import { describe, expect, it } from "vitest";
import {
  SIGN_IN_BAD_ADDRESS,
  SIGN_IN_FAILED,
  SIGN_IN_RATE_LIMITED,
  signInErrorMessage,
} from "./signInErrors";

describe("signInErrorMessage", () => {
  it("passes through the disposable-address refusal", () => {
    const message = "Questo indirizzo email non è accettato. Usa un indirizzo personale.";
    expect(signInErrorMessage({ status: 422, message })).toBe(message);
  });

  it("explains the sign-in email rate limit", () => {
    expect(signInErrorMessage({ status: 429, message: "email rate limit exceeded" })).toBe(SIGN_IN_RATE_LIMITED);
    expect(signInErrorMessage({ code: "over_email_send_rate_limit" })).toBe(SIGN_IN_RATE_LIMITED);
  });

  it("asks to check an invalid address", () => {
    expect(signInErrorMessage({ status: 400, code: "email_address_invalid" })).toBe(SIGN_IN_BAD_ADDRESS);
  });

  it("never shows provider text for other failures", () => {
    expect(signInErrorMessage({ status: 500, message: "Error sending magic link email" })).toBe(SIGN_IN_FAILED);
  });
});
