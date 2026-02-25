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
    <div style={styles.card}>
      <div style={styles.header}>
        <h3 style={styles.title}>
          {zone.municipality} - Zona {zone.zone_code}
        </h3>
        <span style={styles.badge}>{fasciaLabel}</span>
      </div>

      <p style={styles.description}>{zone.description}</p>

      <div style={styles.meta}>
        <span>Zona: {zone.link_zona}</span>
        <span>Semestre: {semester}</span>
        {zone.distance_m && (
          <span style={styles.warning}>
            Zona approssimata ({Math.round(zone.distance_m)}m)
          </span>
        )}
      </div>

      {estimate && (
        <div style={styles.estimateBox}>
          <div style={styles.estimateLabel}>Stima valore</div>
          <div style={styles.estimateValue}>{formatEur(estimate.mid)}</div>
          <div style={styles.estimateRange}>
            {formatEur(estimate.min)} - {formatEur(estimate.max)}
          </div>
          <div style={styles.estimatePer}>
            {estimate.eur_per_m2_range[0].toLocaleString("it-IT")} -{" "}
            {estimate.eur_per_m2_range[1].toLocaleString("it-IT")} EUR/m2
          </div>
        </div>
      )}
    </div>
  );
}

const styles = {
  card: {
    backgroundColor: "white",
    borderRadius: "8px",
    padding: "16px",
    boxShadow: "0 1px 3px rgba(0,0,0,0.12)",
    border: "1px solid #e2e8f0",
  } as React.CSSProperties,
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: "8px",
  } as React.CSSProperties,
  title: {
    margin: 0,
    fontSize: "1.1rem",
    color: "#1a365d",
  } as React.CSSProperties,
  badge: {
    padding: "2px 8px",
    backgroundColor: "#ebf8ff",
    color: "#2b6cb0",
    borderRadius: "12px",
    fontSize: "0.75rem",
    fontWeight: 600,
  } as React.CSSProperties,
  description: {
    margin: "0 0 8px",
    fontSize: "0.85rem",
    color: "#718096",
    lineHeight: 1.4,
  } as React.CSSProperties,
  meta: {
    display: "flex",
    gap: "16px",
    fontSize: "0.75rem",
    color: "#a0aec0",
    marginBottom: "12px",
  } as React.CSSProperties,
  warning: {
    color: "#dd6b20",
    fontWeight: 600,
  } as React.CSSProperties,
  estimateBox: {
    backgroundColor: "#f0fff4",
    border: "1px solid #c6f6d5",
    borderRadius: "6px",
    padding: "12px",
    textAlign: "center",
  } as React.CSSProperties,
  estimateLabel: {
    fontSize: "0.75rem",
    color: "#48bb78",
    fontWeight: 600,
    textTransform: "uppercase",
    letterSpacing: "0.05em",
  } as React.CSSProperties,
  estimateValue: {
    fontSize: "1.5rem",
    fontWeight: 700,
    color: "#22543d",
    margin: "4px 0",
  } as React.CSSProperties,
  estimateRange: {
    fontSize: "0.85rem",
    color: "#38a169",
  } as React.CSSProperties,
  estimatePer: {
    fontSize: "0.75rem",
    color: "#68d391",
    marginTop: "4px",
  } as React.CSSProperties,
};
