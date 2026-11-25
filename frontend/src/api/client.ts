import axios, { isAxiosError } from "axios";
import type { UploadedDocument } from "../types";
import { accessToken } from "../auth/supabase";
import { ApiError, GENERIC_ERROR, NETWORK_ERROR, apiErrorFromResponse, refusalFromBody } from "./refusals";

const API_BASE = import.meta.env.VITE_API_URL || "";

// Every API call carries the session's access token; no cookies are used.
const api = axios.create({ baseURL: `${API_BASE}/api` });

api.interceptors.request.use(async (config) => {
  const token = await accessToken();
  if (token) config.headers.set("Authorization", `Bearer ${token}`);
  return config;
});

async function authHeaders(): Promise<Record<string, string>> {
  const token = await accessToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function toApiError(error: unknown): unknown {
  if (isAxiosError(error)) {
    if (error.response) return new ApiError(refusalFromBody(error.response.data), error.response.status);
    return new ApiError({ code: null, message: NETWORK_ERROR }, 0);
  }
  return error instanceof ApiError ? error : new ApiError({ code: null, message: GENERIC_ERROR }, 0);
}

// Document upload

export async function uploadDocument(file: File): Promise<UploadedDocument> {
  const formData = new FormData();
  formData.append("file", file);

  let data;
  try {
    ({ data } = await api.post("/documents/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    }));
  } catch (error) {
    throw toApiError(error);
  }

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
    headers: { "Content-Type": "application/json", ...(await authHeaders()) },
    body: JSON.stringify({ messages }),
    signal,
  });

  if (!response.ok) {
    throw await apiErrorFromResponse(response);
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
