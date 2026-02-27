import { useState } from "react";

interface InsightCardProps {
  title: string;
  icon: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
}

function InsightCard({ title, icon, children, defaultOpen = false }: InsightCardProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div style={styles.card}>
      <div style={styles.cardHeader} onClick={() => setIsOpen(!isOpen)}>
        <span style={styles.cardIcon}>{icon}</span>
        <span style={styles.cardTitle}>{title}</span>
        <span style={styles.chevron}>{isOpen ? "\u25B2" : "\u25BC"}</span>
      </div>
      {isOpen && <div style={styles.cardBody}>{children}</div>}
    </div>
  );
}

interface AgentIncentivesProps {
  estimatedValue?: number;  // The adjusted estimate total, if available
}

export function AgentIncentives({ estimatedValue }: AgentIncentivesProps) {
  // Dynamic commission math
  const salePrice = estimatedValue || 500000;
  const commissionRate = 0.03;
  const commission = salePrice * commissionRate;
  const extraSalePrice = 10000;
  const extraCommission = extraSalePrice * commissionRate;

  return (
    <div style={styles.container}>
      <h3 style={styles.title}>Capire gli incentivi dell'agente immobiliare</h3>
      <p style={styles.subtitle}>
        Informazioni essenziali per chi vende (o compra) casa
      </p>

      <InsightCard
        title="Il problema Freakonomics"
        icon="\uD83D\uDCCA"
        defaultOpen={true}
      >
        <p style={styles.text}>
          Lo studio di <strong>Levitt & Syvester</strong> (reso celebre nel libro <em>Freakonomics</em>)
          ha rivelato un dato sorprendente: quando gli agenti immobiliari vendono la <strong>propria</strong> casa,
          la tengono sul mercato <strong>10 giorni in piu</strong> e ottengono un prezzo <strong>superiore del 10%</strong> rispetto
          a quando vendono la casa di un cliente.
        </p>
        <div style={styles.mathBox}>
          <div style={styles.mathRow}>
            <span>Prezzo di vendita:</span>
            <span style={styles.mathValue}>{formatEur(salePrice)}</span>
          </div>
          <div style={styles.mathRow}>
            <span>Commissione agente (3%):</span>
            <span style={styles.mathValue}>{formatEur(commission)}</span>
          </div>
          <div style={{ ...styles.mathRow, borderTop: "1px dashed #cbd5e0", paddingTop: "6px" }}>
            <span>Se vende a +{formatEur(extraSalePrice)}:</span>
            <span style={styles.mathValue}>
              +{formatEur(extraCommission)} per l'agente
            </span>
          </div>
        </div>
        <p style={styles.highlight}>
          Un extra di {formatEur(extraSalePrice)} nel prezzo di vendita frutta all'agente solo {formatEur(extraCommission)} in piu
          di commissione, ma potrebbe richiedere settimane di attesa. L'incentivo dell'agente e chiudere in fretta,
          non massimizzare il tuo prezzo.
        </p>
      </InsightCard>

      <InsightCard title="Perche l'agenzia valuta meno" icon="\uD83D\uDCB0">
        <p style={styles.text}>
          Le agenzie spesso usano i valori OMI per lo stato <strong>"NORMALE"</strong> come base,
          senza applicare i coefficienti correttivi per ristrutturazione, piano, silenziosita.
        </p>
        <ul style={styles.list}>
          <li>
            <strong>Valutazione conservativa</strong>: una valutazione bassa attira piu potenziali acquirenti
            e velocizza la vendita
          </li>
          <li>
            <strong>Commissione quasi invariata</strong>: su una differenza di {formatEur(100000)},
            l'agente perde solo {formatEur(100000 * commissionRate)} di commissione
          </li>
          <li>
            <strong>Volume vs. valore</strong>: vendere 10 case al mese a prezzo ribassato rende piu
            di venderne 5 al prezzo giusto
          </li>
        </ul>
        <div style={styles.warningBox}>
          Quando un'agenzia sottovaluta di {formatEur(100000)}, perde solo {formatEur(100000 * commissionRate)} di
          commissione &mdash; ma <strong>tu perdi {formatEur(100000)}</strong>.
        </div>
      </InsightCard>

      <InsightCard title="Dove un buon agente fa la differenza" icon="\u2B50">
        <p style={styles.text}>
          Un agente competente e motivato puo effettivamente giustificare la sua commissione:
        </p>
        <div style={styles.valueGrid}>
          <div style={styles.valueItem}>
            <strong>Conoscenza del mercato</strong>
            <p>Sa quali acquirenti cercano esattamente il tuo tipo di immobile. Ha un database di contatti qualificati.</p>
          </div>
          <div style={styles.valueItem}>
            <strong>Negoziazione professionale</strong>
            <p>Un agente esperto ottiene il 5-10% in piu attraverso tecniche di negoziazione. Il costo della commissione si ripaga.</p>
          </div>
          <div style={styles.valueItem}>
            <strong>Qualificazione acquirenti</strong>
            <p>Filtra i perditempo, verifica la pre-approvazione del mutuo, riduce i rischi di trattative che saltano.</p>
          </div>
          <div style={styles.valueItem}>
            <strong>Home staging</strong>
            <p>Piccoli investimenti (500-2.000 EUR) che rendono 5-10x. Spostare un mobile, una mano di vernice, foto professionali.</p>
          </div>
          <div style={styles.valueItem}>
            <strong>Strategia di prezzo</strong>
            <p>
              L'<em>effetto prime 2 settimane</em>: immobili correttamente prezzati ottengono il 94% del prezzo richiesto.
              Quelli sovraprezzati che restano mesi sul mercato scendono al 90%.
            </p>
          </div>
        </div>
      </InsightCard>

      <InsightCard title="Come scegliere un agente" icon="\uD83D\uDD0D">
        <ol style={styles.numberedList}>
          <li>
            <strong>Chiedi: "Quali vendite comparabili in questo edificio/strada supportano la tua valutazione?"</strong>
            <p style={styles.listDetail}>
              Se non puo citare transazioni specifiche, sta tirando a indovinare.
            </p>
          </li>
          <li>
            <strong>Confronta: ottieni almeno 3 valutazioni</strong>
            <p style={styles.listDetail}>
              Diffida sia della piu bassa (vuole vendere in fretta) che della piu alta (vuole il mandato).
              La valutazione giusta e quella documentata.
            </p>
          </li>
          <li>
            <strong>Negozia la commissione</strong>
            <p style={styles.listDetail}>
              Il 2-3% e la norma in Italia. Evita esclusivita lunghe: massimo 3 mesi con clausola di uscita.
            </p>
          </li>
          <li>
            <strong>Verifica il track record</strong>
            <p style={styles.listDetail}>
              Quante vendite ha concluso nella tua zona? Qual e il rapporto prezzo richiesto / prezzo finale?
              Un buon agente e sopra il 95%.
            </p>
          </li>
        </ol>
      </InsightCard>
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
  container: {
    backgroundColor: "white",
    borderRadius: "8px",
    padding: "16px",
    boxShadow: "0 1px 3px rgba(0,0,0,0.12)",
    border: "1px solid #e2e8f0",
  } as React.CSSProperties,
  title: {
    margin: "0 0 2px",
    fontSize: "1rem",
    color: "#1a365d",
  } as React.CSSProperties,
  subtitle: {
    margin: "0 0 12px",
    fontSize: "0.8rem",
    color: "#718096",
  } as React.CSSProperties,
  card: {
    border: "1px solid #e2e8f0",
    borderRadius: "6px",
    marginBottom: "8px",
    overflow: "hidden",
  } as React.CSSProperties,
  cardHeader: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    padding: "10px 12px",
    backgroundColor: "#f7fafc",
    cursor: "pointer",
    userSelect: "none",
  } as React.CSSProperties,
  cardIcon: {
    fontSize: "1rem",
  } as React.CSSProperties,
  cardTitle: {
    flex: 1,
    fontSize: "0.85rem",
    fontWeight: 600,
    color: "#2d3748",
  } as React.CSSProperties,
  chevron: {
    fontSize: "0.6rem",
    color: "#a0aec0",
  } as React.CSSProperties,
  cardBody: {
    padding: "12px",
    fontSize: "0.8rem",
    lineHeight: 1.5,
    color: "#4a5568",
  } as React.CSSProperties,
  text: {
    margin: "0 0 8px",
  } as React.CSSProperties,
  mathBox: {
    backgroundColor: "#f7fafc",
    border: "1px solid #e2e8f0",
    borderRadius: "6px",
    padding: "10px 12px",
    margin: "8px 0",
  } as React.CSSProperties,
  mathRow: {
    display: "flex",
    justifyContent: "space-between",
    padding: "3px 0",
    fontSize: "0.8rem",
  } as React.CSSProperties,
  mathValue: {
    fontWeight: 600,
    fontFamily: "monospace",
  } as React.CSSProperties,
  highlight: {
    margin: "8px 0 0",
    padding: "8px 10px",
    backgroundColor: "#fffff0",
    border: "1px solid #fefcbf",
    borderRadius: "4px",
    fontSize: "0.8rem",
    lineHeight: 1.4,
    color: "#744210",
  } as React.CSSProperties,
  list: {
    margin: "6px 0",
    paddingLeft: "20px",
    fontSize: "0.8rem",
    lineHeight: 1.6,
  } as React.CSSProperties,
  warningBox: {
    marginTop: "8px",
    padding: "10px 12px",
    backgroundColor: "#fed7d7",
    border: "1px solid #feb2b2",
    borderRadius: "6px",
    fontSize: "0.8rem",
    color: "#742a2a",
    lineHeight: 1.4,
  } as React.CSSProperties,
  valueGrid: {
    display: "flex",
    flexDirection: "column",
    gap: "8px",
    marginTop: "8px",
  } as React.CSSProperties,
  valueItem: {
    padding: "8px 10px",
    backgroundColor: "#f0fff4",
    border: "1px solid #c6f6d5",
    borderRadius: "4px",
    fontSize: "0.78rem",
    lineHeight: 1.4,
  } as React.CSSProperties,
  numberedList: {
    margin: "6px 0",
    paddingLeft: "20px",
    fontSize: "0.8rem",
    lineHeight: 1.5,
  } as React.CSSProperties,
  listDetail: {
    margin: "2px 0 8px",
    color: "#718096",
    fontSize: "0.78rem",
  } as React.CSSProperties,
};
