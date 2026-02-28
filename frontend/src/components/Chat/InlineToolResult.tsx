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
  // Other tools: don't render a card (agent summarizes in text)
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
    <div style={styles.card}>
      <div style={styles.cardHeader}>
        <span style={styles.zoneName}>{zoneName}</span>
        {fasciaLabel && <span style={styles.fasciaBadge}>{fasciaLabel}</span>}
      </div>
      {semester && (
        <div style={styles.semester}>Semestre: {semester}</div>
      )}
      {estimate && (
        <div style={styles.estimateRow}>
          <span style={styles.estimateLabel}>Stima base:</span>
          <span style={styles.estimateValue}>
            {formatEur(estimate.mid as number)}
          </span>
          <span style={styles.estimateRange}>
            ({formatEur(estimate.min as number)} - {formatEur(estimate.max as number)})
          </span>
        </div>
      )}
      {estimate && (
        <div style={styles.eurM2}>
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

  return (
    <div style={{ ...styles.card, borderColor: "#c6f6d5" }}>
      <div style={styles.cardHeader}>
        <span style={styles.zoneName}>Valutazione corretta</span>
        <span style={{
          ...styles.fasciaBadge,
          backgroundColor: totalCoeff >= 0 ? "#c6f6d5" : "#fed7d7",
          color: totalCoeff >= 0 ? "#22543d" : "#742a2a",
        }}>
          {sign}{coeffPct}%
        </span>
      </div>
      <div style={styles.estimateRow}>
        <span style={styles.estimateLabel}>Stima corretta:</span>
        <span style={{ ...styles.estimateValue, color: "#22543d" }}>
          {formatEur(adjusted.total_mid as number)}
        </span>
      </div>
      <div style={styles.estimateRange}>
        {formatEur(adjusted.total_min as number)} - {formatEur(adjusted.total_max as number)}
      </div>
      <div style={styles.eurM2}>
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

const styles = {
  card: {
    marginTop: "8px",
    padding: "10px 12px",
    borderRadius: "8px",
    border: "1px solid #e2e8f0",
    backgroundColor: "#f7fafc",
    fontSize: "0.78rem",
    lineHeight: 1.5,
  } as React.CSSProperties,
  cardHeader: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: "4px",
  } as React.CSSProperties,
  zoneName: {
    fontWeight: 700,
    color: "#1a365d",
    fontSize: "0.82rem",
  } as React.CSSProperties,
  fasciaBadge: {
    fontSize: "0.7rem",
    padding: "1px 8px",
    borderRadius: "10px",
    backgroundColor: "#ebf8ff",
    color: "#2b6cb0",
    fontWeight: 600,
  } as React.CSSProperties,
  semester: {
    fontSize: "0.72rem",
    color: "#a0aec0",
    marginBottom: "4px",
  } as React.CSSProperties,
  estimateRow: {
    display: "flex",
    alignItems: "baseline",
    gap: "6px",
    flexWrap: "wrap" as const,
  } as React.CSSProperties,
  estimateLabel: {
    color: "#718096",
  } as React.CSSProperties,
  estimateValue: {
    fontWeight: 700,
    fontSize: "1rem",
    color: "#2b6cb0",
  } as React.CSSProperties,
  estimateRange: {
    color: "#a0aec0",
    fontSize: "0.74rem",
  } as React.CSSProperties,
  eurM2: {
    color: "#a0aec0",
    fontSize: "0.72rem",
    marginTop: "2px",
  } as React.CSSProperties,
};
