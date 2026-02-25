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
    <div style={{ fontSize: "0.85rem", lineHeight: 1.5 }}>
      <strong>
        {properties.municipality} - {properties.zone_code}
      </strong>
      {fasciaLabel && <span> ({fasciaLabel})</span>}
      <br />
      {properties.description && (
        <span style={{ color: "#718096", fontSize: "0.75rem" }}>
          {properties.description}
        </span>
      )}
      {properties.price_min != null && properties.price_max != null && (
        <div style={{ marginTop: "4px", fontWeight: 600 }}>
          {properties.price_min.toLocaleString("it-IT")} -{" "}
          {properties.price_max.toLocaleString("it-IT")} EUR/m2
        </div>
      )}
    </div>
  );
}
