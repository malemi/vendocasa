import axios from "axios";
import type { UploadedDocument } from "../types";

const API_BASE = import.meta.env.VITE_API_URL || "";

const api = axios.create({
  baseURL: `${API_BASE}/api`,
  withCredentials: true,
});

// Document upload

export async function uploadDocument(file: File): Promise<UploadedDocument> {
  const formData = new FormData();
  formData.append("file", file);

  const { data } = await api.post("/documents/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });

  return {
    docId: data.doc_id,
    filename: data.filename,
    size: data.size,
    mediaType: data.media_type,
  };
}

// Chat streaming (uses fetch, not axios, for SSE support)

export interface StreamChatEvent {
  type: "text_delta" | "tool_result" | "map_update" | "done" | "error";
  data: Record<string, unknown>;
}

export async function streamChat(
  messages: { role: string; content: string; document_ids?: string[] }[],
  onEvent: (event: StreamChatEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages }),
    credentials: "include",
    signal,
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Chat request failed (${response.status}): ${text}`);
  }

  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    let eventType = "";
    let eventData = "";

    for (const line of lines) {
      if (line.startsWith("event: ")) {
        eventType = line.slice(7);
      } else if (line.startsWith("data: ")) {
        eventData = line.slice(6);
      } else if (line === "" && eventType && eventData) {
        try {
          onEvent({
            type: eventType as StreamChatEvent["type"],
            data: JSON.parse(eventData),
          });
        } catch {
          // skip malformed events
        }
        eventType = "";
        eventData = "";
      }
    }
  }
}
