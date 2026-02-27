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
