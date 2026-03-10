import { FASCIA_LABELS } from "../../types";

interface ZonePopupProps {
  properties: {
    link_zona: string;
    zone_code: string;
    fascia: string | null;
    municipality: string | null;
    description: string | null;
    price_min: number | null;
    price_max: number | null;
  };
}

export function ZonePopup({ properties }: ZonePopupProps) {
  const fasciaLabel = properties.fascia
    ? FASCIA_LABELS[properties.fascia] || properties.fascia
    : "";

  return (
    <div className="text-[0.85rem] leading-normal">
      <strong>
        {properties.municipality} - {properties.zone_code}
      </strong>
      {fasciaLabel && <span> ({fasciaLabel})</span>}
      <br />
      {properties.description && (
        <span className="text-[#718096] text-[0.75rem]">
          {properties.description}
        </span>
      )}
      {properties.price_min != null && properties.price_max != null && (
        <div className="mt-1 font-semibold">
          {properties.price_min.toLocaleString("it-IT")} -{" "}
          {properties.price_max.toLocaleString("it-IT")} EUR/m2
        </div>
      )}
    </div>
  );
}
