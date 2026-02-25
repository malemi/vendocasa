import { useQuery } from "@tanstack/react-query";
import { getSemesters, getZonesGeoJSON } from "../api/client";

export function useZonesGeoJSON(params?: {
  bbox?: string;
  semester?: string;
}) {
  return useQuery({
    queryKey: ["zones-geojson", params],
    queryFn: () => getZonesGeoJSON(params),
  });
}

export function useSemesters() {
  return useQuery({
    queryKey: ["semesters"],
    queryFn: getSemesters,
  });
}
