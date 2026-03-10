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
    <div className="bg-bg-elevated rounded-lg p-4 shadow-sm border border-border">
      {/* Header row with title + step indicator */}
      <div className="flex justify-between items-center mb-3">
        <h3 className="m-0 text-base text-accent font-semibold">
          Valutazione avanzata
        </h3>
        <div className="flex gap-1.5">
          {[1, 2, 3].map((s) => (
            <span
              key={s}
              className={`
                w-6 h-6 rounded-full flex items-center justify-center
                text-[0.7rem] font-bold cursor-pointer transition-colors
                ${s <= step
                  ? "bg-accent text-bg-primary"
                  : "bg-bg-surface text-text-tertiary"
                }
              `}
              onClick={() => s < step && setStep(s)}
            >
              {s}
            </span>
          ))}
        </div>
      </div>

      {/* Step 1: Conservation State */}
      {step === 1 && (
        <ConservationStep
          details={details}
          quotationsByState={quotationsByState}
          onUpdate={updateDetail}
          onNext={() => setStep(2)}
        />
      )}

      {/* Step 2: Property Details */}
      {step === 2 && (
        <DetailsStep
          details={details}
          totalPct={totalPct}
          isLoading={isLoading}
          onUpdate={updateDetail}
          onBack={() => setStep(1)}
          onCalculate={handleCalculate}
        />
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

/* ── Step 1: Conservation State ─────────────────────────── */

function ConservationStep({
  details,
  quotationsByState,
  onUpdate,
  onNext,
}: {
  details: PropertyDetails;
  quotationsByState: Record<string, { min: number; max: number; prevalent: boolean }>;
  onUpdate: (factor: string, value: string) => void;
  onNext: () => void;
}) {
  return (
    <div className="flex flex-col gap-2.5">
      <p className="m-0 text-[0.9rem] font-semibold text-text-primary">
        Qual e lo stato conservativo del tuo immobile?
      </p>
      <p className="m-0 text-[0.8rem] text-text-tertiary leading-snug">
        La differenza tra NORMALE e OTTIMO puo essere del 30-50%. Scegli lo stato che meglio descrive il tuo immobile.
      </p>

      {CONSERVATION_STATES.map((cs) => {
        const range = quotationsByState[cs.key];
        const isSelected = details.conservation_state === cs.key;
        return (
          <div
            key={cs.key}
            className={`
              border-2 rounded-md px-3 py-2.5 cursor-pointer transition-all
              ${isSelected
                ? "border-accent bg-accent/10"
                : "border-border bg-bg-surface hover:border-border-light"
              }
            `}
            onClick={() => onUpdate("conservation_state", cs.key)}
          >
            <div className="flex justify-between items-center text-[0.85rem]">
              <strong className="text-text-primary">{cs.label}</strong>
              {range && (
                <span className="text-[0.75rem] text-accent font-semibold">
                  {range.min.toLocaleString("it-IT")} - {range.max.toLocaleString("it-IT")} EUR/m2
                  {range.prevalent && (
                    <span className="ml-1.5 px-1.5 py-px rounded-full bg-success-muted text-success text-[0.65rem]">
                      prevalente
                    </span>
                  )}
                </span>
              )}
            </div>
            <p className="m-0 mt-1 text-[0.75rem] text-text-tertiary">{cs.desc}</p>
          </div>
        );
      })}

      <button
        className="self-end px-4 py-2 bg-accent text-bg-primary border-none rounded-md text-[0.85rem] font-semibold cursor-pointer hover:bg-accent-hover transition-colors"
        onClick={onNext}
      >
        Avanti &rarr;
      </button>
    </div>
  );
}

/* ── Step 2: Property Details ────────────────────────────── */

function DetailsStep({
  details,
  totalPct,
  isLoading,
  onUpdate,
  onBack,
  onCalculate,
}: {
  details: PropertyDetails;
  totalPct: number;
  isLoading: boolean;
  onUpdate: (factor: string, value: string) => void;
  onBack: () => void;
  onCalculate: () => void;
}) {
  return (
    <div className="flex flex-col gap-2.5">
      <p className="m-0 text-[0.9rem] font-semibold text-text-primary">
        Dettagli dell'immobile
      </p>
      <p className="m-0 text-[0.8rem] text-text-tertiary leading-snug">
        Seleziona le caratteristiche specifiche. L'impatto sul valore e mostrato accanto a ogni opzione.
      </p>

      {Object.entries(FACTOR_OPTIONS).map(([factor, config]) => (
        <div key={factor} className="flex flex-col gap-0.5">
          <label className="text-[0.8rem] font-semibold text-text-secondary">
            {config.label}
          </label>
          <select
            className="px-2 py-1.5 rounded border border-border text-[0.8rem] bg-bg-surface text-text-primary outline-none focus:border-accent/50 focus:ring-1 focus:ring-accent/20 transition-colors"
            value={details[factor as keyof PropertyDetails]}
            onChange={(e) => onUpdate(factor, e.target.value)}
          >
            {config.options.map((opt) => (
              <option key={opt.key} value={opt.key}>
                {opt.label} ({formatPct(opt.pct)})
              </option>
            ))}
          </select>
        </div>
      ))}

      {/* Live coefficient preview */}
      <div className="flex justify-between items-center px-3 py-2 bg-bg-surface rounded-md border border-border">
        <span className="text-[0.8rem] text-text-secondary font-semibold">
          Coefficiente totale:
        </span>
        <span className={`text-lg font-bold font-mono ${totalPct >= 0 ? "text-success" : "text-danger"}`}>
          {formatPct(totalPct)}
        </span>
      </div>

      <div className="flex gap-2 justify-between">
        <button
          className="px-4 py-2 bg-bg-surface text-text-secondary border border-border rounded-md text-[0.85rem] cursor-pointer hover:bg-bg-primary hover:text-text-primary transition-colors"
          onClick={onBack}
        >
          &larr; Indietro
        </button>
        <button
          className="px-5 py-2 bg-success text-white border-none rounded-md text-[0.85rem] font-semibold cursor-pointer hover:bg-success/80 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          onClick={onCalculate}
          disabled={isLoading}
        >
          {isLoading ? "Calcolo..." : "Calcola valutazione"}
        </button>
      </div>
    </div>
  );
}

/* ── Step 3: Enhanced Results ────────────────────────────── */

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
    return (
      <div className="py-5 text-center text-text-tertiary text-[0.9rem]">
        Calcolo in corso...
      </div>
    );
  }

  // Client-side calculation preview
  const base = quotationsByState[details.conservation_state] ||
    quotationsByState["NORMALE"] ||
    Object.values(quotationsByState)[0];

  if (!base) {
    return (
      <div className="p-2.5 bg-danger-muted text-danger rounded-md text-[0.85rem]">
        Nessun dato quotazione disponibile per questa zona.
      </div>
    );
  }

  const multiplier = 1 + totalPct;
  const adjMin = base.min * multiplier;
  const adjMax = base.max * multiplier;
  const adjMid = (adjMin + adjMax) / 2;
  const surface = basicValuation.estimate?.mid
    ? basicValuation.estimate.mid / ((basicValuation.estimate.eur_per_m2_range[0] + basicValuation.estimate.eur_per_m2_range[1]) / 2)
    : 0;

  return (
    <div className="flex flex-col gap-2.5">
      {/* Main result card */}
      <div className="bg-accent/10 border border-accent/30 rounded-md p-3.5 text-center">
        <div className="text-[0.75rem] text-accent font-semibold uppercase tracking-wide">
          Stima corretta
        </div>
        <div className="text-2xl font-bold text-accent my-1 font-mono">
          {formatEur(adjMid * (surface || 1))}
        </div>
        <div className="text-[0.85rem] text-accent/80 font-mono">
          {formatEur(adjMin * (surface || 1))} - {formatEur(adjMax * (surface || 1))}
        </div>
        <div className="text-[0.75rem] text-text-tertiary mt-1 font-mono">
          {adjMin.toLocaleString("it-IT", { maximumFractionDigits: 0 })} -{" "}
          {adjMax.toLocaleString("it-IT", { maximumFractionDigits: 0 })} EUR/m2
          <span className={`
            ml-2 px-2 py-0.5 rounded-full text-[0.7rem] font-bold
            ${totalPct >= 0 ? "bg-success-muted text-success" : "bg-danger-muted text-danger"}
          `}>
            {formatPct(totalPct)}
          </span>
        </div>
      </div>

      {/* Breakdown table */}
      <div className="mt-1">
        <h4 className="m-0 mb-1.5 text-[0.85rem] text-text-primary">
          Dettaglio coefficienti
        </h4>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-[0.75rem]">
            <thead>
              <tr>
                <th className="p-1.5 px-2 text-left border-b-2 border-border text-text-secondary font-semibold">
                  Fattore
                </th>
                <th className="p-1.5 px-2 text-left border-b-2 border-border text-text-secondary font-semibold">
                  Selezione
                </th>
                <th className="p-1.5 px-2 text-right border-b-2 border-border text-text-secondary font-semibold">
                  Coefficiente
                </th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-border/50">
                <td className="p-1.5 px-2 text-text-secondary">Stato conservativo</td>
                <td className="p-1.5 px-2 text-text-secondary">{details.conservation_state}</td>
                <td className="p-1.5 px-2 text-right text-text-tertiary">base</td>
              </tr>
              {Object.entries(FACTOR_OPTIONS).map(([factor, config]) => {
                const selected = details[factor as keyof PropertyDetails];
                const option = config.options.find((o) => o.key === selected);
                if (!option) return null;
                return (
                  <tr key={factor} className="border-b border-border/50">
                    <td className="p-1.5 px-2 text-text-secondary">{config.label}</td>
                    <td className="p-1.5 px-2 text-text-secondary">{option.label}</td>
                    <td className={`
                      p-1.5 px-2 text-right font-mono
                      ${option.pct > 0 ? "text-success font-semibold" : ""}
                      ${option.pct < 0 ? "text-danger font-semibold" : ""}
                      ${option.pct === 0 ? "text-text-tertiary" : ""}
                    `}>
                      {formatPct(option.pct)}
                    </td>
                  </tr>
                );
              })}
              <tr className="border-t-2 border-accent">
                <td className="p-1.5 px-2 font-bold text-text-primary" colSpan={2}>
                  Totale coefficiente correttivo
                </td>
                <td className={`
                  p-1.5 px-2 text-right font-bold font-mono
                  ${totalPct >= 0 ? "text-success" : "text-danger"}
                `}>
                  {formatPct(totalPct)}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Comparison with basic estimate */}
      {basicValuation.estimate && (
        <div className="bg-bg-surface border border-border rounded-md px-3 py-2.5 text-[0.8rem]">
          <div className="flex justify-between py-0.5">
            <span className="text-text-secondary">Stima base OMI:</span>
            <span className="text-text-primary font-mono">
              {formatEur(basicValuation.estimate.mid)}
            </span>
          </div>
          <div className="flex justify-between py-0.5">
            <span className="text-text-secondary">Stima corretta:</span>
            <span className="font-bold text-accent font-mono">
              {formatEur(adjMid * (surface || 1))}
            </span>
          </div>
          <div className="flex justify-between py-0.5">
            <span className="text-text-secondary">Differenza:</span>
            <span className={`
              font-semibold font-mono
              ${adjMid * (surface || 1) > basicValuation.estimate.mid ? "text-success" : "text-danger"}
            `}>
              {formatEur(adjMid * (surface || 1) - basicValuation.estimate.mid)}
            </span>
          </div>
        </div>
      )}

      <button
        className="px-4 py-2 bg-bg-surface text-text-secondary border border-border rounded-md text-[0.85rem] cursor-pointer hover:bg-bg-primary hover:text-text-primary transition-colors self-start"
        onClick={() => window.location.reload()}
      >
        Nuova valutazione
      </button>
    </div>
  );
}
