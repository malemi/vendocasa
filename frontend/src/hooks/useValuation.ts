import { useQuery } from "@tanstack/react-query";
import { valuate } from "../api/client";

export function useValuation(params: {
  address: string;
  property_type?: number;
  surface_m2?: number;
  semester?: string;
}) {
  return useQuery({
    queryKey: ["valuation", params],
    queryFn: () => valuate(params),
    enabled: !!params.address,
  });
}
