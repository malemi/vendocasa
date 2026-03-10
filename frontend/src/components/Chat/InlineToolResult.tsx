/**
 * Compact inline cards for tool results displayed within chat messages.
 */

interface InlineToolResultProps {
  tool: string;
  result: Record<string, unknown>;
}

export function InlineToolResult({ tool, result }: InlineToolResultProps) {
  if (tool === "valuate_property") {
    return <BasicValuationCard result={result} />;
  }
  if (tool === "enhanced_valuate_property") {
    return <EnhancedValuationCard result={result} />;
  }
  return null;
}

function BasicValuationCard({ result }: { result: Record<string, unknown> }) {
  const zone = result.zone as Record<string, unknown> | undefined;
  const estimate = result.estimate as Record<string, unknown> | undefined;
  const semester = result.semester as string | undefined;

  if (!zone) return null;

  const zoneName = `${zone.municipality || ""} - Zona ${zone.zone_code || ""}`;
  const fascia = zone.fascia as string;
  const fasciaLabel =
    fascia === "B" ? "Centrale" :
    fascia === "C" ? "Semicentrale" :
    fascia === "D" ? "Periferica" :
    fascia === "E" ? "Suburbana" :
    fascia === "R" ? "Rurale" : fascia;

  return (
    <div className="mt-2 p-3 rounded-lg bg-bg-elevated border border-border text-xs leading-relaxed">
      <div className="flex items-center justify-between mb-1">
        <span className="font-bold text-accent text-[0.82rem]">{zoneName}</span>
        {fasciaLabel && (
          <span className="text-[0.7rem] px-2 py-0.5 rounded-full bg-teal-muted text-teal font-semibold">
            {fasciaLabel}
          </span>
        )}
      </div>
      {semester && (
        <div className="text-text-tertiary text-[0.72rem] mb-1">
          Semestre: {semester}
        </div>
      )}
      {estimate && (
        <div className="flex items-baseline gap-1.5 flex-wrap">
          <span className="text-text-secondary">Stima base:</span>
          <span className="font-bold text-base text-accent">
            {formatEur(estimate.mid as number)}
          </span>
          <span className="text-text-tertiary text-[0.74rem]">
            ({formatEur(estimate.min as number)} - {formatEur(estimate.max as number)})
          </span>
        </div>
      )}
      {estimate && (
        <div className="text-text-tertiary text-[0.72rem] mt-0.5 font-mono">
          {(estimate.eur_per_m2_range as number[])?.[0]} - {(estimate.eur_per_m2_range as number[])?.[1]} EUR/m2
        </div>
      )}
    </div>
  );
}

function EnhancedValuationCard({ result }: { result: Record<string, unknown> }) {
  const adjusted = result.adjusted_estimate as Record<string, unknown> | undefined;
  if (!adjusted) return null;

  const totalCoeff = adjusted.total_coefficient as number;
  const coeffPct = (totalCoeff * 100).toFixed(0);
  const sign = totalCoeff >= 0 ? "+" : "";
  const isPositive = totalCoeff >= 0;

  return (
    <div className={`mt-2 p-3 rounded-lg bg-bg-elevated border ${isPositive ? "border-success/30" : "border-danger/30"} text-xs leading-relaxed`}>
      <div className="flex items-center justify-between mb-1">
        <span className="font-bold text-accent text-[0.82rem]">Valutazione corretta</span>
        <span
          className={`
            text-[0.7rem] px-2 py-0.5 rounded-full font-semibold
            ${isPositive ? "bg-success-muted text-success" : "bg-danger-muted text-danger"}
          `}
        >
          {sign}{coeffPct}%
        </span>
      </div>
      <div className="flex items-baseline gap-1.5 flex-wrap">
        <span className="text-text-secondary">Stima corretta:</span>
        <span className={`font-bold text-base ${isPositive ? "text-success" : "text-danger"}`}>
          {formatEur(adjusted.total_mid as number)}
        </span>
      </div>
      <div className="text-text-tertiary text-[0.74rem]">
        {formatEur(adjusted.total_min as number)} - {formatEur(adjusted.total_max as number)}
      </div>
      <div className="text-text-tertiary text-[0.72rem] mt-0.5 font-mono">
        {Math.round(adjusted.adjusted_price_min as number)} - {Math.round(adjusted.adjusted_price_max as number)} EUR/m2
        (base {String(adjusted.base_conservation_state)}: {Math.round(adjusted.base_price_min as number)} - {Math.round(adjusted.base_price_max as number)})
      </div>
    </div>
  );
}

function formatEur(value: number): string {
  return new Intl.NumberFormat("it-IT", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 0,
  }).format(value);
}
