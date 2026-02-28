import axios from "axios";
import type {
  EnhancedValuationResponse,
  PropertyDetails,
  SemesterList,
  TransactionInput,
  TransactionRecord,
  ValuationResponse,
  ZoneGeoJSON,
} from "../types";

const API_BASE = import.meta.env.VITE_API_URL || "";

const api = axios.create({
  baseURL: `${API_BASE}/api`,
});

export async function valuate(params: {
  address: string;
  property_type?: number;
  surface_m2?: number;
  semester?: string;
}): Promise<ValuationResponse> {
  const { data } = await api.get("/valuate", { params });
  return data;
}

export async function enhancedValuate(params: {
  address: string;
  surface_m2: number;
  property_type?: number;
  semester?: string;
  details: PropertyDetails;
}): Promise<EnhancedValuationResponse> {
  const { data } = await api.post("/valuate/enhanced", {
    address: params.address,
    surface_m2: params.surface_m2,
    property_type: params.property_type || 20,
    semester: params.semester || null,
    details: params.details,
  });
  return data;
}

export async function getZonesGeoJSON(params?: {
  bbox?: string;
  semester?: string;
}): Promise<ZoneGeoJSON> {
  const { data } = await api.get("/zones/geojson", { params });
  return data;
}

export async function getSemesters(): Promise<SemesterList> {
  const { data } = await api.get("/semesters");
  return data;
}

export async function getQuotations(params: {
  link_zona: string;
  semester?: string;
}) {
  const { data } = await api.get("/quotations", { params });
  return data;
}

export async function createTransaction(
  input: TransactionInput
): Promise<TransactionRecord> {
  const { data } = await api.post("/transactions", input);
  return data;
}

export async function getTransactions(params?: {
  link_zona?: string;
  municipality?: string;
}): Promise<TransactionRecord[]> {
  const { data } = await api.get("/transactions", { params });
  return data;
}

export async function deleteTransaction(id: number): Promise<void> {
  await api.delete(`/transactions/${id}`);
}

// Chat streaming (uses fetch, not axios, for SSE support)

export interface StreamChatEvent {
  type: "text_delta" | "tool_result" | "map_update" | "done" | "error";
  data: Record<string, unknown>;
}

export async function streamChat(
  messages: { role: string; content: string }[],
  onEvent: (event: StreamChatEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages }),
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
