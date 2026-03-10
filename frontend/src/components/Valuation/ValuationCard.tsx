import type { ValuationResponse } from "../../types";
import { FASCIA_LABELS } from "../../types";

interface ValuationCardProps {
  data: ValuationResponse;
}

function formatEur(value: number): string {
  return new Intl.NumberFormat("it-IT", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 0,
  }).format(value);
}

export function ValuationCard({ data }: ValuationCardProps) {
  const { zone, estimate, semester } = data;
  const fasciaLabel = zone.fascia ? FASCIA_LABELS[zone.fascia] || zone.fascia : "";

  return (
    <div className="bg-bg-elevated rounded-xl p-4 shadow-sm border border-border">
      <div className="flex justify-between items-center mb-2">
        <h3 className="m-0 text-lg text-accent font-bold">
          {zone.municipality} - Zona {zone.zone_code}
        </h3>
        <span className="px-2.5 py-0.5 bg-teal-muted text-teal rounded-full text-xs font-semibold">
          {fasciaLabel}
        </span>
      </div>

      <p className="mb-2 text-sm text-text-secondary leading-snug">{zone.description}</p>

      <div className="flex gap-4 text-xs text-text-tertiary mb-3">
        <span>Zona: {zone.link_zona}</span>
        <span>Semestre: {semester}</span>
        {zone.distance_m && (
          <span className="text-accent font-semibold">
            Zona approssimata ({Math.round(zone.distance_m)}m)
          </span>
        )}
      </div>

      {estimate && (
        <div className="bg-success-muted border border-success/30 rounded-lg p-3 text-center">
          <div className="text-xs text-success font-semibold uppercase tracking-wide">
            Stima valore
          </div>
          <div className="text-2xl font-bold text-success my-1 font-mono">
            {formatEur(estimate.mid)}
          </div>
          <div className="text-sm text-success/80">
            {formatEur(estimate.min)} - {formatEur(estimate.max)}
          </div>
          <div className="text-xs text-success/60 mt-1 font-mono">
            {estimate.eur_per_m2_range[0].toLocaleString("it-IT")} -{" "}
            {estimate.eur_per_m2_range[1].toLocaleString("it-IT")} EUR/m2
          </div>
        </div>
      )}
    </div>
  );
}
