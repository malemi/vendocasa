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
    <div className="border border-border rounded-md mb-2 overflow-hidden">
      <div
        className="flex items-center gap-2 px-3 py-2.5 bg-bg-surface cursor-pointer select-none hover:bg-bg-surface/80 transition-colors"
        onClick={() => setIsOpen(!isOpen)}
      >
        <span className="text-base">{icon}</span>
        <span className="flex-1 text-sm font-semibold text-text-primary">{title}</span>
        <span className="text-[0.6rem] text-text-tertiary">{isOpen ? "\u25B2" : "\u25BC"}</span>
      </div>
      {isOpen && (
        <div className="p-3 text-xs leading-relaxed text-text-secondary">
          {children}
        </div>
      )}
    </div>
  );
}

interface AgentIncentivesProps {
  estimatedValue?: number;
}

export function AgentIncentives({ estimatedValue }: AgentIncentivesProps) {
  const salePrice = estimatedValue || 500000;
  const commissionRate = 0.03;
  const commission = salePrice * commissionRate;
  const extraSalePrice = 10000;
  const extraCommission = extraSalePrice * commissionRate;

  return (
    <div className="bg-bg-elevated rounded-lg p-4 shadow-md border border-border">
      <h3 className="mb-0.5 text-base text-text-primary">
        Capire gli incentivi dell'agente immobiliare
      </h3>
      <p className="mb-3 text-xs text-text-tertiary">
        Informazioni essenziali per chi vende (o compra) casa
      </p>

      <InsightCard title="Il problema Freakonomics" icon="📊" defaultOpen={true}>
        <p className="mb-2">
          Lo studio di <strong className="text-text-primary">Levitt & Syvester</strong> (reso celebre nel libro <em>Freakonomics</em>)
          ha rivelato un dato sorprendente: quando gli agenti immobiliari vendono la <strong className="text-text-primary">propria</strong> casa,
          la tengono sul mercato <strong className="text-text-primary">10 giorni in piu</strong> e ottengono un prezzo <strong className="text-text-primary">superiore del 10%</strong> rispetto
          a quando vendono la casa di un cliente.
        </p>
        <div className="bg-bg-surface border border-border rounded-md px-3 py-2.5 my-2">
          <div className="flex justify-between py-0.5 text-xs">
            <span>Prezzo di vendita:</span>
            <span className="font-semibold font-mono text-text-primary">{formatEur(salePrice)}</span>
          </div>
          <div className="flex justify-between py-0.5 text-xs">
            <span>Commissione agente (3%):</span>
            <span className="font-semibold font-mono text-text-primary">{formatEur(commission)}</span>
          </div>
          <div className="flex justify-between py-0.5 text-xs border-t border-dashed border-border-light pt-1.5">
            <span>Se vende a +{formatEur(extraSalePrice)}:</span>
            <span className="font-semibold font-mono text-text-primary">
              +{formatEur(extraCommission)} per l'agente
            </span>
          </div>
        </div>
        <p className="mt-2 px-2.5 py-2 bg-accent-muted border border-accent/30 rounded text-xs leading-snug text-accent">
          Un extra di {formatEur(extraSalePrice)} nel prezzo di vendita frutta all'agente solo {formatEur(extraCommission)} in piu
          di commissione, ma potrebbe richiedere settimane di attesa. L'incentivo dell'agente e chiudere in fretta,
          non massimizzare il tuo prezzo.
        </p>
      </InsightCard>

      <InsightCard title="Perche l'agenzia valuta meno" icon="💰">
        <p className="mb-2">
          Le agenzie spesso usano i valori OMI per lo stato <strong className="text-text-primary">"NORMALE"</strong> come base,
          senza applicare i coefficienti correttivi per ristrutturazione, piano, silenziosita.
        </p>
        <ul className="my-1.5 pl-5 text-xs leading-relaxed list-disc">
          <li>
            <strong className="text-text-primary">Valutazione conservativa</strong>: una valutazione bassa attira piu potenziali acquirenti
            e velocizza la vendita
          </li>
          <li>
            <strong className="text-text-primary">Commissione quasi invariata</strong>: su una differenza di {formatEur(100000)},
            l'agente perde solo {formatEur(100000 * commissionRate)} di commissione
          </li>
          <li>
            <strong className="text-text-primary">Volume vs. valore</strong>: vendere 10 case al mese a prezzo ribassato rende piu
            di venderne 5 al prezzo giusto
          </li>
        </ul>
        <div className="mt-2 px-3 py-2.5 bg-danger-muted border border-danger/30 rounded-md text-xs text-danger leading-snug">
          Quando un'agenzia sottovaluta di {formatEur(100000)}, perde solo {formatEur(100000 * commissionRate)} di
          commissione &mdash; ma <strong>tu perdi {formatEur(100000)}</strong>.
        </div>
      </InsightCard>

      <InsightCard title="Dove un buon agente fa la differenza" icon={"\u2B50"}>
        <p className="mb-2">
          Un agente competente e motivato puo effettivamente giustificare la sua commissione:
        </p>
        <div className="flex flex-col gap-2 mt-2">
          <div className="px-2.5 py-2 bg-success-muted border border-success/30 rounded text-[0.78rem] leading-snug">
            <strong className="text-success">Conoscenza del mercato</strong>
            <p className="text-text-secondary mt-0.5">Sa quali acquirenti cercano esattamente il tuo tipo di immobile. Ha un database di contatti qualificati.</p>
          </div>
          <div className="px-2.5 py-2 bg-success-muted border border-success/30 rounded text-[0.78rem] leading-snug">
            <strong className="text-success">Negoziazione professionale</strong>
            <p className="text-text-secondary mt-0.5">Un agente esperto ottiene il 5-10% in piu attraverso tecniche di negoziazione. Il costo della commissione si ripaga.</p>
          </div>
          <div className="px-2.5 py-2 bg-success-muted border border-success/30 rounded text-[0.78rem] leading-snug">
            <strong className="text-success">Qualificazione acquirenti</strong>
            <p className="text-text-secondary mt-0.5">Filtra i perditempo, verifica la pre-approvazione del mutuo, riduce i rischi di trattative che saltano.</p>
          </div>
          <div className="px-2.5 py-2 bg-success-muted border border-success/30 rounded text-[0.78rem] leading-snug">
            <strong className="text-success">Home staging</strong>
            <p className="text-text-secondary mt-0.5">Piccoli investimenti (500-2.000 EUR) che rendono 5-10x. Spostare un mobile, una mano di vernice, foto professionali.</p>
          </div>
          <div className="px-2.5 py-2 bg-success-muted border border-success/30 rounded text-[0.78rem] leading-snug">
            <strong className="text-success">Strategia di prezzo</strong>
            <p className="text-text-secondary mt-0.5">
              L'<em>effetto prime 2 settimane</em>: immobili correttamente prezzati ottengono il 94% del prezzo richiesto.
              Quelli sovraprezzati che restano mesi sul mercato scendono al 90%.
            </p>
          </div>
        </div>
      </InsightCard>

      <InsightCard title="Come scegliere un agente" icon="🔍">
        <ol className="my-1.5 pl-5 text-xs leading-relaxed list-decimal">
          <li>
            <strong className="text-text-primary">"Quali vendite comparabili in questo edificio/strada supportano la tua valutazione?"</strong>
            <p className="mt-0.5 mb-2 text-text-tertiary text-[0.78rem]">
              Se non puo citare transazioni specifiche, sta tirando a indovinare.
            </p>
          </li>
          <li>
            <strong className="text-text-primary">Confronta: ottieni almeno 3 valutazioni</strong>
            <p className="mt-0.5 mb-2 text-text-tertiary text-[0.78rem]">
              Diffida sia della piu bassa (vuole vendere in fretta) che della piu alta (vuole il mandato).
              La valutazione giusta e quella documentata.
            </p>
          </li>
          <li>
            <strong className="text-text-primary">Negozia la commissione</strong>
            <p className="mt-0.5 mb-2 text-text-tertiary text-[0.78rem]">
              Il 2-3% e la norma in Italia. Evita esclusivita lunghe: massimo 3 mesi con clausola di uscita.
            </p>
          </li>
          <li>
            <strong className="text-text-primary">Verifica il track record</strong>
            <p className="mt-0.5 mb-2 text-text-tertiary text-[0.78rem]">
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
