import { useState } from "react";
import type { ValuationResponse, PropertyDetails } from "../../types";

interface CoefficientWizardProps {
  basicValuation: ValuationResponse;
  isLoading: boolean;
  onSubmit: (details: PropertyDetails) => void;
}

const CONSERVATION_STATES = [
  { key: "OTTIMO", label: "Ottimo", desc: "Ristrutturato con finiture di pregio, impianti nuovi certificati" },
  { key: "NORMALE", label: "Normale", desc: "Buone condizioni generali, manutenzione ordinaria" },
  { key: "SCADENTE", label: "Scadente", desc: "Necessita interventi significativi, impianti datati" },
];

const FACTOR_OPTIONS: Record<string, { label: string; options: { key: string; label: string; pct: number }[] }> = {
  renovation: {
    label: "Ristrutturazione",
    options: [
      { key: "premium_post_2015", label: "Integrale post-2015 (certificata)", pct: 0.10 },
      { key: "standard_recent", label: "Parziale / recente", pct: 0.05 },
      { key: "none", label: "Nessuna", pct: 0.0 },
      { key: "needs_work", label: "Da ristrutturare", pct: -0.10 },
    ],
  },
  floor: {
    label: "Piano",
    options: [
      { key: "ground_semi", label: "Piano terra / seminterrato", pct: -0.05 },
      { key: "first", label: "Primo piano", pct: -0.02 },
      { key: "second", label: "Secondo piano", pct: 0.0 },
      { key: "third_fourth", label: "Terzo / quarto piano", pct: 0.05 },
      { key: "fifth_plus", label: "Quinto piano e oltre", pct: 0.04 },
      { key: "penthouse", label: "Attico / ultimo piano", pct: 0.08 },
    ],
  },
  exposure: {
    label: "Esposizione / Luminosita",
    options: [
      { key: "south_dual", label: "Sud / doppia esposizione", pct: 0.05 },
      { key: "east_west", label: "Est / Ovest", pct: 0.02 },
      { key: "north_only", label: "Solo Nord", pct: -0.05 },
      { key: "internal_dark", label: "Interno / poco luminoso", pct: -0.08 },
    ],
  },
  noise: {
    label: "Rumorosita",
    options: [
      { key: "very_silent", label: "Molto silenzioso", pct: 0.03 },
      { key: "silent_courtyard", label: "Cortile interno / silenzioso", pct: 0.02 },
      { key: "normal", label: "Normale", pct: 0.0 },
      { key: "street_moderate", label: "Strada moderata", pct: -0.02 },
      { key: "busy_street", label: "Strada trafficata", pct: -0.05 },
    ],
  },
  elevator: {
    label: "Ascensore",
    options: [
      { key: "yes", label: "Presente", pct: 0.0 },
      { key: "no_low_floor", label: "Assente (piano basso)", pct: 0.0 },
      { key: "no_high_floor", label: "Assente (piano alto)", pct: -0.05 },
    ],
  },
  common_areas: {
    label: "Parti comuni",
    options: [
      { key: "excellent", label: "Ottime condizioni", pct: 0.02 },
      { key: "good", label: "Buone condizioni", pct: 0.0 },
      { key: "needs_maintenance", label: "Necessita manutenzione", pct: -0.02 },
      { key: "poor", label: "Cattive condizioni", pct: -0.05 },
      { key: "serious_neglect", label: "Gravi carenze", pct: -0.07 },
    ],
  },
  building_facade: {
    label: "Facciata edificio",
    options: [
      { key: "recently_restored", label: "Recentemente restaurata", pct: 0.02 },
      { key: "good_condition", label: "Buone condizioni", pct: 0.0 },
      { key: "needs_work", label: "Necessita intervento", pct: -0.02 },
      { key: "visibly_degraded", label: "Visibilmente degradata", pct: -0.05 },
    ],
  },
  energy_class: {
    label: "Classe energetica",
    options: [
      { key: "A_B", label: "Classe A o B", pct: 0.05 },
      { key: "C_D", label: "Classe C o D", pct: 0.02 },
      { key: "E", label: "Classe E", pct: 0.0 },
      { key: "F_G", label: "Classe F o G", pct: -0.05 },
    ],
  },
};

const DEFAULT_DETAILS: PropertyDetails = {
  conservation_state: "NORMALE",
  renovation: "none",
  floor: "second",
  exposure: "east_west",
  noise: "normal",
  elevator: "yes",
  common_areas: "good",
  building_facade: "good_condition",
  energy_class: "E",
};

function formatPct(pct: number): string {
  if (pct === 0) return "0%";
  return `${pct > 0 ? "+" : ""}${(pct * 100).toFixed(0)}%`;
}

function formatEur(value: number): string {
  return new Intl.NumberFormat("it-IT", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 0,
  }).format(value);
}

export function CoefficientWizard({ basicValuation, isLoading, onSubmit }: CoefficientWizardProps) {
  const [step, setStep] = useState(1);
  const [details, setDetails] = useState<PropertyDetails>({ ...DEFAULT_DETAILS });

  const updateDetail = (factor: string, value: string) => {
    setDetails((prev) => ({ ...prev, [factor]: value }));
  };

  const handleCalculate = () => {
    onSubmit(details);
    setStep(3);
  };

  // Show quotation ranges by conservation state from the basic valuation
  const quotationsByState: Record<string, { min: number; max: number; prevalent: boolean }> = {};
  for (const q of basicValuation.quotations) {
    if (q.conservation_state && q.price_min && q.price_max) {
      quotationsByState[q.conservation_state] = {
        min: q.price_min,
        max: q.price_max,
        prevalent: q.is_prevalent,
      };
    }
  }

  // Compute a live preview of total coefficient
  let totalPct = 0;
  for (const [factor, opts] of Object.entries(FACTOR_OPTIONS)) {
    const selected = details[factor as keyof PropertyDetails];
    const option = opts.options.find((o) => o.key === selected);
    if (option) totalPct += option.pct;
  }

  return (
    <div style={styles.container}>
      <div style={styles.headerRow}>
        <h3 style={styles.title}>Valutazione avanzata</h3>
        <div style={styles.stepIndicator}>
          {[1, 2, 3].map((s) => (
            <span
              key={s}
              style={{
                ...styles.stepDot,
                backgroundColor: s <= step ? "#2b6cb0" : "#e2e8f0",
                color: s <= step ? "#fff" : "#a0aec0",
              }}
              onClick={() => s < step && setStep(s)}
            >
              {s}
            </span>
          ))}
        </div>
      </div>

      {/* Step 1: Conservation State */}
      {step === 1 && (
        <div style={styles.stepContent}>
          <p style={styles.stepLabel}>
            Qual e lo stato conservativo del tuo immobile?
          </p>
          <p style={styles.hint}>
            La differenza tra NORMALE e OTTIMO puo essere del 30-50%. Scegli lo stato che meglio descrive il tuo immobile.
          </p>
          {CONSERVATION_STATES.map((cs) => {
            const range = quotationsByState[cs.key];
            const isSelected = details.conservation_state === cs.key;
            return (
              <div
                key={cs.key}
                style={{
                  ...styles.stateCard,
                  borderColor: isSelected ? "#2b6cb0" : "#e2e8f0",
                  backgroundColor: isSelected ? "#ebf8ff" : "#fff",
                }}
                onClick={() => updateDetail("conservation_state", cs.key)}
              >
                <div style={styles.stateHeader}>
                  <strong>{cs.label}</strong>
                  {range && (
                    <span style={styles.stateRange}>
                      {range.min.toLocaleString("it-IT")} - {range.max.toLocaleString("it-IT")} EUR/m2
                      {range.prevalent && <span style={styles.prevalentBadge}>prevalente</span>}
                    </span>
                  )}
                </div>
                <p style={styles.stateDesc}>{cs.desc}</p>
              </div>
            );
          })}
          <button style={styles.nextBtn} onClick={() => setStep(2)}>
            Avanti &rarr;
          </button>
        </div>
      )}

      {/* Step 2: Property Details */}
      {step === 2 && (
        <div style={styles.stepContent}>
          <p style={styles.stepLabel}>Dettagli dell'immobile</p>
          <p style={styles.hint}>
            Seleziona le caratteristiche specifiche. L'impatto sul valore e mostrato accanto a ogni opzione.
          </p>

          {Object.entries(FACTOR_OPTIONS).map(([factor, config]) => (
            <div key={factor} style={styles.factorGroup}>
              <label style={styles.factorLabel}>{config.label}</label>
              <select
                style={styles.select}
                value={details[factor as keyof PropertyDetails]}
                onChange={(e) => updateDetail(factor, e.target.value)}
              >
                {config.options.map((opt) => (
                  <option key={opt.key} value={opt.key}>
                    {opt.label} ({formatPct(opt.pct)})
                  </option>
                ))}
              </select>
            </div>
          ))}

          <div style={styles.previewBox}>
            <span style={styles.previewLabel}>Coefficiente totale:</span>
            <span style={{
              ...styles.previewValue,
              color: totalPct >= 0 ? "#22543d" : "#9b2c2c",
            }}>
              {formatPct(totalPct)}
            </span>
          </div>

          <div style={styles.buttonRow}>
            <button style={styles.backBtn} onClick={() => setStep(1)}>
              &larr; Indietro
            </button>
            <button
              style={styles.calculateBtn}
              onClick={handleCalculate}
              disabled={isLoading}
            >
              {isLoading ? "Calcolo..." : "Calcola valutazione"}
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Results */}
      {step === 3 && (
        <EnhancedResults
          isLoading={isLoading}
          details={details}
          basicValuation={basicValuation}
          totalPct={totalPct}
          quotationsByState={quotationsByState}
        />
      )}
    </div>
  );
}

function EnhancedResults({
  isLoading,
  details,
  basicValuation,
  totalPct,
  quotationsByState,
}: {
  isLoading: boolean;
  details: PropertyDetails;
  basicValuation: ValuationResponse;
  totalPct: number;
  quotationsByState: Record<string, { min: number; max: number; prevalent: boolean }>;
}) {
  if (isLoading) {
    return <div style={styles.loading}>Calcolo in corso...</div>;
  }

  // Client-side calculation preview (actual server response would be better)
  const base = quotationsByState[details.conservation_state] ||
    quotationsByState["NORMALE"] ||
    Object.values(quotationsByState)[0];

  if (!base) {
    return <div style={styles.error}>Nessun dato quotazione disponibile per questa zona.</div>;
  }

  const multiplier = 1 + totalPct;
  const adjMin = base.min * multiplier;
  const adjMax = base.max * multiplier;
  const adjMid = (adjMin + adjMax) / 2;
  const surface = basicValuation.estimate?.mid
    ? basicValuation.estimate.mid / ((basicValuation.estimate.eur_per_m2_range[0] + basicValuation.estimate.eur_per_m2_range[1]) / 2)
    : 0;

  return (
    <div style={styles.stepContent}>
      <div style={styles.resultBox}>
        <div style={styles.resultLabel}>Stima corretta</div>
        <div style={styles.resultValue}>
          {formatEur(adjMid * (surface || 1))}
        </div>
        <div style={styles.resultRange}>
          {formatEur(adjMin * (surface || 1))} - {formatEur(adjMax * (surface || 1))}
        </div>
        <div style={styles.resultPer}>
          {adjMin.toLocaleString("it-IT", { maximumFractionDigits: 0 })} -{" "}
          {adjMax.toLocaleString("it-IT", { maximumFractionDigits: 0 })} EUR/m2
          <span style={styles.coeffBadge}>{formatPct(totalPct)}</span>
        </div>
      </div>

      {/* Breakdown table */}
      <div style={styles.breakdownContainer}>
        <h4 style={styles.breakdownTitle}>Dettaglio coefficienti</h4>
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={styles.th}>Fattore</th>
              <th style={styles.th}>Selezione</th>
              <th style={{ ...styles.th, textAlign: "right" }}>Coefficiente</th>
            </tr>
          </thead>
          <tbody>
            <tr style={styles.tr}>
              <td style={styles.td}>Stato conservativo</td>
              <td style={styles.td}>{details.conservation_state}</td>
              <td style={{ ...styles.td, textAlign: "right" }}>base</td>
            </tr>
            {Object.entries(FACTOR_OPTIONS).map(([factor, config]) => {
              const selected = details[factor as keyof PropertyDetails];
              const option = config.options.find((o) => o.key === selected);
              if (!option) return null;
              return (
                <tr key={factor} style={styles.tr}>
                  <td style={styles.td}>{config.label}</td>
                  <td style={styles.td}>{option.label}</td>
                  <td style={{
                    ...styles.td,
                    textAlign: "right",
                    color: option.pct > 0 ? "#22543d" : option.pct < 0 ? "#9b2c2c" : "#718096",
                    fontWeight: option.pct !== 0 ? 600 : 400,
                  }}>
                    {formatPct(option.pct)}
                  </td>
                </tr>
              );
            })}
            <tr style={{ ...styles.tr, borderTop: "2px solid #2b6cb0" }}>
              <td style={{ ...styles.td, fontWeight: 700 }} colSpan={2}>
                Totale coefficiente correttivo
              </td>
              <td style={{
                ...styles.td,
                textAlign: "right",
                fontWeight: 700,
                color: totalPct >= 0 ? "#22543d" : "#9b2c2c",
              }}>
                {formatPct(totalPct)}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Comparison with basic estimate */}
      {basicValuation.estimate && (
        <div style={styles.comparisonBox}>
          <div style={styles.comparisonRow}>
            <span>Stima base OMI:</span>
            <span>{formatEur(basicValuation.estimate.mid)}</span>
          </div>
          <div style={styles.comparisonRow}>
            <span>Stima corretta:</span>
            <span style={{ fontWeight: 700, color: "#2b6cb0" }}>
              {formatEur(adjMid * (surface || 1))}
            </span>
          </div>
          <div style={styles.comparisonRow}>
            <span>Differenza:</span>
            <span style={{
              fontWeight: 600,
              color: adjMid * (surface || 1) > basicValuation.estimate.mid ? "#22543d" : "#9b2c2c",
            }}>
              {formatEur(adjMid * (surface || 1) - basicValuation.estimate.mid)}
            </span>
          </div>
        </div>
      )}

      <button style={styles.backBtn} onClick={() => window.location.reload()}>
        Nuova valutazione
      </button>
    </div>
  );
}

const styles = {
  container: {
    backgroundColor: "white",
    borderRadius: "8px",
    padding: "16px",
    boxShadow: "0 1px 3px rgba(0,0,0,0.12)",
    border: "1px solid #e2e8f0",
  } as React.CSSProperties,
  headerRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: "12px",
  } as React.CSSProperties,
  title: {
    margin: 0,
    fontSize: "1rem",
    color: "#1a365d",
  } as React.CSSProperties,
  stepIndicator: {
    display: "flex",
    gap: "6px",
  } as React.CSSProperties,
  stepDot: {
    width: "24px",
    height: "24px",
    borderRadius: "50%",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: "0.7rem",
    fontWeight: 700,
    cursor: "pointer",
  } as React.CSSProperties,
  stepContent: {
    display: "flex",
    flexDirection: "column",
    gap: "10px",
  } as React.CSSProperties,
  stepLabel: {
    margin: 0,
    fontSize: "0.9rem",
    fontWeight: 600,
    color: "#2d3748",
  } as React.CSSProperties,
  hint: {
    margin: 0,
    fontSize: "0.8rem",
    color: "#718096",
    lineHeight: 1.4,
  } as React.CSSProperties,
  stateCard: {
    border: "2px solid #e2e8f0",
    borderRadius: "6px",
    padding: "10px 12px",
    cursor: "pointer",
    transition: "all 0.15s",
  } as React.CSSProperties,
  stateHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    fontSize: "0.85rem",
  } as React.CSSProperties,
  stateRange: {
    fontSize: "0.75rem",
    color: "#2b6cb0",
    fontWeight: 600,
  } as React.CSSProperties,
  prevalentBadge: {
    marginLeft: "6px",
    padding: "1px 6px",
    backgroundColor: "#c6f6d5",
    color: "#22543d",
    borderRadius: "8px",
    fontSize: "0.65rem",
  } as React.CSSProperties,
  stateDesc: {
    margin: "4px 0 0",
    fontSize: "0.75rem",
    color: "#718096",
  } as React.CSSProperties,
  factorGroup: {
    display: "flex",
    flexDirection: "column",
    gap: "3px",
  } as React.CSSProperties,
  factorLabel: {
    fontSize: "0.8rem",
    fontWeight: 600,
    color: "#4a5568",
  } as React.CSSProperties,
  select: {
    padding: "6px 8px",
    borderRadius: "4px",
    border: "1px solid #e2e8f0",
    fontSize: "0.8rem",
    backgroundColor: "#fff",
  } as React.CSSProperties,
  previewBox: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "8px 12px",
    backgroundColor: "#f7fafc",
    borderRadius: "6px",
    border: "1px solid #e2e8f0",
  } as React.CSSProperties,
  previewLabel: {
    fontSize: "0.8rem",
    color: "#4a5568",
    fontWeight: 600,
  } as React.CSSProperties,
  previewValue: {
    fontSize: "1.1rem",
    fontWeight: 700,
  } as React.CSSProperties,
  buttonRow: {
    display: "flex",
    gap: "8px",
    justifyContent: "space-between",
  } as React.CSSProperties,
  nextBtn: {
    padding: "8px 16px",
    backgroundColor: "#2b6cb0",
    color: "#fff",
    border: "none",
    borderRadius: "6px",
    fontSize: "0.85rem",
    fontWeight: 600,
    cursor: "pointer",
    alignSelf: "flex-end",
  } as React.CSSProperties,
  backBtn: {
    padding: "8px 16px",
    backgroundColor: "#edf2f7",
    color: "#4a5568",
    border: "none",
    borderRadius: "6px",
    fontSize: "0.85rem",
    cursor: "pointer",
  } as React.CSSProperties,
  calculateBtn: {
    padding: "8px 20px",
    backgroundColor: "#38a169",
    color: "#fff",
    border: "none",
    borderRadius: "6px",
    fontSize: "0.85rem",
    fontWeight: 600,
    cursor: "pointer",
  } as React.CSSProperties,
  loading: {
    padding: "20px",
    textAlign: "center",
    color: "#718096",
    fontSize: "0.9rem",
  } as React.CSSProperties,
  error: {
    padding: "10px",
    backgroundColor: "#fed7d7",
    color: "#9b2c2c",
    borderRadius: "6px",
    fontSize: "0.85rem",
  } as React.CSSProperties,
  resultBox: {
    backgroundColor: "#ebf8ff",
    border: "1px solid #bee3f8",
    borderRadius: "6px",
    padding: "14px",
    textAlign: "center",
  } as React.CSSProperties,
  resultLabel: {
    fontSize: "0.75rem",
    color: "#2b6cb0",
    fontWeight: 600,
    textTransform: "uppercase",
    letterSpacing: "0.05em",
  } as React.CSSProperties,
  resultValue: {
    fontSize: "1.6rem",
    fontWeight: 700,
    color: "#1a365d",
    margin: "4px 0",
  } as React.CSSProperties,
  resultRange: {
    fontSize: "0.85rem",
    color: "#2b6cb0",
  } as React.CSSProperties,
  resultPer: {
    fontSize: "0.75rem",
    color: "#63b3ed",
    marginTop: "4px",
  } as React.CSSProperties,
  coeffBadge: {
    marginLeft: "8px",
    padding: "2px 8px",
    backgroundColor: "#2b6cb0",
    color: "#fff",
    borderRadius: "10px",
    fontSize: "0.7rem",
    fontWeight: 700,
  } as React.CSSProperties,
  breakdownContainer: {
    marginTop: "4px",
  } as React.CSSProperties,
  breakdownTitle: {
    margin: "0 0 6px",
    fontSize: "0.85rem",
    color: "#2d3748",
  } as React.CSSProperties,
  table: {
    width: "100%",
    borderCollapse: "collapse",
    fontSize: "0.75rem",
  } as React.CSSProperties,
  th: {
    padding: "6px 8px",
    textAlign: "left",
    borderBottom: "2px solid #e2e8f0",
    color: "#4a5568",
    fontWeight: 600,
  } as React.CSSProperties,
  tr: {
    borderBottom: "1px solid #f7fafc",
  } as React.CSSProperties,
  td: {
    padding: "5px 8px",
    color: "#4a5568",
  } as React.CSSProperties,
  comparisonBox: {
    backgroundColor: "#fffff0",
    border: "1px solid #fefcbf",
    borderRadius: "6px",
    padding: "10px 12px",
    fontSize: "0.8rem",
  } as React.CSSProperties,
  comparisonRow: {
    display: "flex",
    justifyContent: "space-between",
    padding: "3px 0",
  } as React.CSSProperties,
};
