/**
 * The user's journeys through the built frontend, in order, in one browser:
 * sign-in with an emailed link, a valuation, the approximate-location warning,
 * the re-upload of an expired attachment, the history limit, keyboard use of
 * the chat panel, the ledger's record of every call, and sign-out.
 */

import { expect, test, type BrowserContext, type Page } from "@playwright/test";
import { API_URL, MICRO_USD_PER_CALL, OWNER_EMAIL, api, loadStatus, sessionFor, signInLinkFor } from "./stack";

test.describe.configure({ mode: "serial" });

const status = loadStatus();
const userEmail = `utente-${Date.now()}@vendocasa.test`;
const PANEL = '[aria-label="VendoCasa — Chat"]';
// A one-page PDF, enough for the upload checks.
const MINIMAL_PDF =
  "%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n" +
  "3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n";

let context: BrowserContext;
let page: Page;
let ownerToken: string;
let modelCalls = 0;

test.beforeAll(async ({ browser }) => {
  // Paid calls are off by default; the owner turns them on through the owner route.
  ownerToken = await sessionFor(status, OWNER_EMAIL);
  const switched = await api("/api/admin/paid-calls", ownerToken, {
    method: "PUT",
    body: JSON.stringify({ enabled: true }),
  });
  expect(switched.status).toBe(200);
  context = await browser.newContext();
  page = await context.newPage();
});

test.afterAll(async () => {
  await context?.close();
});

/** Sends a message and waits until its answer has finished streaming. */
async function send(text: string, calls: number) {
  const box = page.locator(`${PANEL} textarea`);
  await box.fill(text);
  await box.press("Enter");
  await expect(page.getByTitle("Ferma")).toHaveCount(0, { timeout: 30_000 });
  await expect(page.getByTitle("Invia")).toBeVisible();
  modelCalls += calls;
}

async function focusIsInsidePanel(): Promise<boolean> {
  return page.evaluate((selector) => document.activeElement?.closest(selector) != null, PANEL);
}

test("a new address signs in with the emailed link and reaches the chat", async () => {
  await page.goto("/");
  await page.getByRole("button", { name: "Valuta ora" }).first().click();
  await page.getByRole("button", { name: "Accetto" }).click();
  await page.getByLabel("Email").fill(userEmail);
  await page.getByRole("button", { name: "Inviami il link" }).click();
  await expect(page.getByText("Ti abbiamo inviato un link a")).toBeVisible();

  await page.goto(await signInLinkFor(status, userEmail));
  await expect(page.getByText("Ciao! Sono il tuo consulente")).toBeVisible();
  await expect(page.getByRole("button", { name: "Esci" })).toBeVisible();
});

test("a valuation shows the zone's quotations and reports its comparable sales", async () => {
  await send("Valuta Via Roma 10, Milano, 80 mq", 2);
  await expect(page.getByText("MILANO - Zona B01")).toBeVisible();
  await expect(page.getByText("Semestre: 2024_S2")).toBeVisible();
  await expect(page.getByText("Stima base:")).toBeVisible();
  // The answer is built from the tool result, so these come from the database.
  await expect(page.getByText(/Quotazione OMI NORMALE: 2100(\.0+)?-2800(\.0+)? EUR\/m2/).first()).toBeVisible();
  await expect(page.getByText(/Compravendite comparabili: 3\./).first()).toBeVisible();
  await expect(page.getByText(/232500(\.0+)? EUR/).first()).toBeVisible();
  // An exact location carries no warning.
  await expect(page.getByRole("note")).toHaveCount(0);
});

test("an approximate location is flagged in Italian", async () => {
  await send("Valuta Via Incerta, Milano, 80 mq", 2);
  const note = page.getByRole("note");
  await expect(note).toHaveCount(1);
  await expect(note).toContainText("Posizione approssimativa: verifica che l'indirizzo sia corretto.");
  await expect(note).toContainText("Indirizzo trovato: Milano.");
});

test("an attachment that expired on the server is uploaded again and sent", async () => {
  const uploads: string[] = [];
  page.on("request", (request) => {
    if (request.url() === `${API_URL}/api/documents/upload` && request.method() === "POST") {
      uploads.push(request.method());
    }
  });
  await page.locator(`${PANEL} input[type="file"]`).setInputFiles({
    name: "visura.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from(MINIMAL_PDF),
  });
  await expect(page.getByText("visura.pdf")).toBeVisible();
  // The journey server expires uploads after 4 seconds.
  await page.waitForTimeout(6_000);
  await send("Analizza la visura.", 1);
  await expect(page.getByText("Allegati ricevuti: 1.")).toBeVisible();
  await expect(page.getByText("Un documento allegato è scaduto")).toHaveCount(0);
  expect(uploads).toEqual(["POST", "POST"]);
});

test("at the history limit the chat offers a new conversation, which starts clean", async () => {
  const banner = page.getByText("La conversazione ha raggiunto la lunghezza massima.");
  for (let turn = 0; turn < 30 && !(await banner.isVisible()); turn++) {
    await send(`Domanda ${turn}`, 1);
  }
  await expect(banner).toBeVisible();
  await expect(page.getByTitle("Invia")).toBeDisabled();
  await expect(page.locator(`${PANEL} button[title="Allega PDF o foto"]`)).toBeDisabled();

  await page.getByRole("button", { name: "Nuova conversazione" }).click();
  await expect(banner).toHaveCount(0);
  await expect(page.getByText("Risposta di prova.")).toHaveCount(0);
  await send("Domanda dopo la nuova conversazione", 1);
  await expect(page.getByText("Risposta di prova.")).toHaveCount(1);
});

test("the open panel keeps keyboard focus and returns it; the closed panel is unreachable", async () => {
  await page.keyboard.press("Escape");
  await expect(page.locator(PANEL)).toHaveAttribute("inert", "");

  // Closed: Tab never reaches a control inside the panel.
  await page.locator("body").focus();
  for (let i = 0; i < 40; i++) {
    await page.keyboard.press("Tab");
    expect(await focusIsInsidePanel()).toBe(false);
  }

  // Opened from the keyboard: focus moves in and stays in, both directions.
  const opener = page.getByRole("button", { name: "Valuta ora" }).first();
  await opener.focus();
  await page.keyboard.press("Enter");
  await expect(page.locator(PANEL)).not.toHaveAttribute("inert", "");
  expect(await focusIsInsidePanel()).toBe(true);
  for (const key of ["Tab", "Shift+Tab"]) {
    for (let i = 0; i < 15; i++) {
      await page.keyboard.press(key);
      expect(await focusIsInsidePanel()).toBe(true);
    }
  }

  // Escape closes it, and focus goes back to the button that opened it.
  await page.keyboard.press("Escape");
  await expect(opener).toBeFocused();
  await opener.click();
});

test("the ledger charged every model call of this account once, and settled all of them", async () => {
  const userId = await page.evaluate(() => {
    const key = Object.keys(localStorage).find((k) => k.endsWith("-auth-token"));
    return key ? (JSON.parse(localStorage.getItem(key) as string).user.id as string) : null;
  });
  expect(userId).not.toBeNull();
  const report = await api("/api/admin/spending", ownerToken);
  expect(report.status).toBe(200);
  const { accounts, paid_calls_enabled } = (await report.json()) as {
    paid_calls_enabled: boolean;
    accounts: Array<{ account_id: string; spent_usd: number; reserved_usd: number }>;
  };
  expect(paid_calls_enabled).toBe(true);
  const mine = accounts.find((a) => a.account_id === userId);
  expect(mine).toBeDefined();
  expect(mine!.reserved_usd).toBe(0);
  expect(Math.round(mine!.spent_usd * 1_000_000)).toBe(modelCalls * MICRO_USD_PER_CALL);
});

test("signing out ends the session in this browser", async () => {
  await page.getByRole("button", { name: "Esci" }).click();
  await expect(page.getByRole("heading", { name: "Accedi a VendoCasa" })).toBeVisible();
  const stored = await page.evaluate(() => Object.keys(localStorage).filter((k) => k.endsWith("-auth-token")));
  expect(stored).toEqual([]);
  // Without the session, a protected route refuses the browser.
  const refused = await page.evaluate(async (url) => (await fetch(`${url}/api/transactions`)).status, API_URL);
  expect(refused).toBe(401);
});
