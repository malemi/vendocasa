export interface Coordinates {
  lat: number;
  lng: number;
}

export interface ZoneInfo {
  link_zona: string;
  zone_code: string;
  fascia: string | null;
  municipality: string | null;
  description: string | null;
  distance_m: number | null;
}

export interface QuotationItem {
  property_type_desc: string | null;
  conservation_state: string | null;
  is_prevalent: boolean;
  price_min: number | null;
  price_max: number | null;
  surface_type_sale: string | null;
  rent_min: number | null;
  rent_max: number | null;
  surface_type_rent: string | null;
}

export interface Estimate {
  min: number;
  max: number;
  mid: number;
  eur_per_m2_range: [number, number];
}

export interface ComparableItem {
  transaction_date: string | null;
  declared_price: number | null;
  cadastral_category: string | null;
  cadastral_vani: number | null;
  cadastral_mq: number | null;
  notes: string | null;
}

export interface ValuationResponse {
  address: string;
  coordinates: Coordinates;
  zone: ZoneInfo;
  semester: string;
  quotations: QuotationItem[];
  estimate: Estimate | null;
  comparables: ComparableItem[];
}

export interface SemesterList {
  semesters: string[];
  latest: string | null;
}

export interface TransactionInput {
  transaction_date?: string;
  transaction_type?: string;
  declared_price?: number;
  municipality?: string;
  omi_zone?: string;
  link_zona?: string;
  cadastral_category?: string;
  cadastral_vani?: number;
  cadastral_mq?: number;
  cadastral_mc?: number;
  notes?: string;
}

export interface TransactionRecord extends TransactionInput {
  id: number;
  created_at: string;
}

export interface ZoneGeoJSON {
  type: "FeatureCollection";
  features: Array<{
    type: "Feature";
    geometry: GeoJSON.Geometry;
    properties: {
      link_zona: string;
      zone_code: string;
      fascia: string | null;
      municipality: string | null;
      description: string | null;
      price_min: number | null;
      price_max: number | null;
    };
  }>;
}

// Property type options for the UI
export const PROPERTY_TYPES = [
  { code: 20, label: "Abitazioni civili" },
  { code: 21, label: "Abitazioni economiche" },
  { code: 1, label: "Ville e villini" },
  { code: 2, label: "Abitazioni signorili" },
  { code: 13, label: "Box" },
  { code: 11, label: "Negozi" },
  { code: 6, label: "Uffici" },
] as const;

export const FASCIA_LABELS: Record<string, string> = {
  B: "Centrale",
  C: "Semicentrale",
  D: "Periferica",
  E: "Suburbana",
  R: "Rurale",
};

// Enhanced valuation types (coefficient wizard)

export interface PropertyDetails {
  conservation_state: string;
  renovation: string;
  floor: string;
  exposure: string;
  noise: string;
  elevator: string;
  common_areas: string;
  building_facade: string;
  energy_class: string;
  [key: string]: string;  // allow dynamic access by factor name
}

export interface CoefficientBreakdownItem {
  factor: string;
  factor_label: string;
  selected_key: string;
  selected_label: string;
  coefficient: number;
  impact_eur_m2: number;
}

export interface BenchmarkComparison {
  has_comparables: boolean;
  closest_eur_m2: number | null;
  difference_pct: number | null;
  confidence: string;
  note: string;
}

export interface AdjustedEstimate {
  base_price_min: number;
  base_price_max: number;
  base_conservation_state: string;
  total_coefficient: number;
  adjusted_price_min: number;
  adjusted_price_max: number;
  adjusted_mid: number;
  total_min: number;
  total_max: number;
  total_mid: number;
  surface_m2: number;
  breakdown: CoefficientBreakdownItem[];
  benchmark_comparison: BenchmarkComparison | null;
}

export interface EnhancedValuationResponse {
  address: string;
  coordinates: Coordinates;
  zone: ZoneInfo;
  semester: string;
  quotations_by_state: Record<string, {
    price_min: number;
    price_max: number;
    is_prevalent: boolean;
    surface_type_sale: string | null;
  }>;
  adjusted_estimate: AdjustedEstimate;
  comparables: ComparableItem[];
}
