import axios from "axios";
import type {
  SemesterList,
  TransactionInput,
  TransactionRecord,
  ValuationResponse,
  ZoneGeoJSON,
} from "../types";

const api = axios.create({
  baseURL: "/api",
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
