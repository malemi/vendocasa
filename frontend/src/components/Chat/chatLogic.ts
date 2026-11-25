/**
 * Pure helpers for the chat panel, kept out of the component so they can be
 * tested without a browser.
 */

import type { ChatMessage, UploadedDocument } from "../../types";

/** Messages the backend accepts in one request (AGENT_MAX_HISTORY_MESSAGES). */
export const MAX_HISTORY_MESSAGES = 50;

/** True when sending one more message would exceed the history limit. */
export function conversationAtLimit(messages: ChatMessage[], max = MAX_HISTORY_MESSAGES): boolean {
  const sent = messages.filter((m) => m.id !== "welcome").length;
  return sent + 1 > max;
}

/**
 * Upload again the documents whose server copy expired, from the files kept in
 * memory. Returns the replacement documents, or null when a file is no longer
 * available and the user must attach it again.
 */
export async function reuploadDocuments(
  documents: UploadedDocument[],
  upload: (file: File) => Promise<UploadedDocument>,
): Promise<UploadedDocument[] | null> {
  if (documents.length === 0 || documents.some((d) => !d.file)) return null;
  const replaced: UploadedDocument[] = [];
  for (const doc of documents) {
    const fresh = await upload(doc.file as File);
    replaced.push({ ...fresh, file: doc.file });
  }
  return replaced;
}

/** The Italian notice for an approximate location, or null when it is exact. */
export function locationNotice(result: Record<string, unknown>): string | null {
  const location = result.location as
    | { approximate?: boolean; matched_address?: string | null; zone_distance_m?: number | null }
    | undefined;
  if (!location || !location.approximate) return null;
  const parts = ["Posizione approssimativa: verifica che l'indirizzo sia corretto."];
  if (location.matched_address) parts.push(`Indirizzo trovato: ${location.matched_address}.`);
  if (location.zone_distance_m && location.zone_distance_m > 0) {
    parts.push(`Usata la zona OMI più vicina, a circa ${Math.round(location.zone_distance_m)} m.`);
  }
  return parts.join(" ");
}

/** The no-data message of a valuation result, or null. */
export function noDataNotice(result: Record<string, unknown>): string | null {
  const noData = result.no_data as { message?: string } | undefined;
  return noData?.message ?? null;
}
