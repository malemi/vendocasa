import { describe, expect, it } from "vitest";
import type { ChatMessage, UploadedDocument } from "../../types";
import {
  MAX_HISTORY_MESSAGES,
  conversationAtLimit,
  locationNotice,
  noDataNotice,
  reuploadDocuments,
} from "./chatLogic";

const message = (id: string): ChatMessage => ({ id, role: "user", content: "x" });

describe("conversationAtLimit", () => {
  it("allows sending until the next message would exceed the limit", () => {
    const welcome = { ...message("welcome"), role: "assistant" as const };
    const below = [welcome, ...Array.from({ length: MAX_HISTORY_MESSAGES - 1 }, (_, i) => message(`m${i}`))];
    expect(conversationAtLimit(below)).toBe(false); // the welcome message is not sent
    expect(conversationAtLimit([...below, message("last")])).toBe(true);
  });
});

describe("reuploadDocuments", () => {
  const file = new File(["%PDF-1.4"], "visura.pdf", { type: "application/pdf" });
  const expired: UploadedDocument = { docId: "old", filename: "visura.pdf", size: 8, mediaType: "application/pdf", file };

  it("uploads the kept files again and keeps them for a later expiry", async () => {
    const uploaded: File[] = [];
    const result = await reuploadDocuments([expired], async (f) => {
      uploaded.push(f);
      return { docId: "new", filename: f.name, size: f.size, mediaType: f.type };
    });
    expect(uploaded).toEqual([file]);
    expect(result).toEqual([{ docId: "new", filename: "visura.pdf", size: 8, mediaType: "application/pdf", file }]);
  });

  it("gives up when a file is no longer in memory", async () => {
    const withoutFile = { ...expired, file: undefined };
    expect(await reuploadDocuments([withoutFile], async () => expired)).toBeNull();
  });
});

describe("notices", () => {
  it("explains an approximate location in Italian", () => {
    const notice = locationNotice({
      location: { approximate: true, matched_address: "Via Roma, Milano", zone_distance_m: 120.4 },
    });
    expect(notice).toContain("Posizione approssimativa");
    expect(notice).toContain("Via Roma, Milano");
    expect(notice).toContain("120 m");
    expect(locationNotice({ location: { approximate: false } })).toBeNull();
    expect(locationNotice({})).toBeNull();
  });

  it("shows the no-data message", () => {
    expect(noDataNotice({ no_data: { message: "Nessuna quotazione OMI utilizzabile." } })).toBe(
      "Nessuna quotazione OMI utilizzabile.",
    );
    expect(noDataNotice({ estimate: {} })).toBeNull();
  });
});
