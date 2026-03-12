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
  const underPriced = salePrice * 0.9;
  const overPriced = salePrice * 1.15;

  return (
    <div className="bg-bg-elevated rounded-lg p-4 shadow-md border border-border">
      <h3 className="mb-0.5 text-base text-text-primary">
        Vendere al prezzo giusto
      </h3>
      <p className="mb-3 text-xs text-text-tertiary">
        Informazioni essenziali per chi vende (o compra) casa
      </p>

      <InsightCard title="Conosci il valore reale" icon="📊" defaultOpen={true}>
        <p className="mb-2">
          Prima di mettere in vendita, e fondamentale conoscere il <strong className="text-text-primary">valore reale</strong> del
          tuo immobile. I dati dell'<strong className="text-text-primary">Osservatorio del Mercato Immobiliare</strong> (OMI)
          dell'Agenzia delle Entrate forniscono range di prezzo aggiornati per ogni micro-zona d'Italia.
        </p>
        <div className="bg-bg-surface border border-border rounded-md px-3 py-2.5 my-2">
          <div className="flex justify-between py-0.5 text-xs">
            <span>Valore stimato del tuo immobile:</span>
            <span className="font-semibold font-mono text-text-primary">{formatEur(salePrice)}</span>
          </div>
          <div className="flex justify-between py-0.5 text-xs">
            <span>Sottovalutato (rischi di svendere):</span>
            <span className="font-semibold font-mono text-danger">{formatEur(underPriced)}</span>
          </div>
          <div className="flex justify-between py-0.5 text-xs border-t border-dashed border-border-light pt-1.5">
            <span>Sopravvalutato (rischi di non vendere):</span>
            <span className="font-semibold font-mono text-text-tertiary">{formatEur(overPriced)}</span>
          </div>
        </div>
        <p className="mt-2 px-2.5 py-2 bg-accent-muted border border-accent/30 rounded text-xs leading-snug text-accent">
          Partire informati significa poter dialogare con qualsiasi professionista da una posizione di consapevolezza,
          non di debolezza. VendoCasa ti da i dati: le decisioni le prendi tu.
        </p>
      </InsightCard>

      <InsightCard title="Due errori opposti da evitare" icon="⚖️">
        <p className="mb-2">
          Nella vendita immobiliare ci sono <strong className="text-text-primary">due errori simmetrici</strong>,
          ed entrambi costano caro:
        </p>

        <div className="mt-2 px-3 py-2.5 bg-danger-muted border border-danger/30 rounded-md text-xs text-danger leading-snug mb-3">
          <strong>Sottovalutare:</strong> accettare un'offerta troppo bassa per chiudere in fretta.
          Su un immobile da {formatEur(salePrice)}, vendere a {formatEur(underPriced)} significa
          lasciare {formatEur(salePrice - underPriced)} sul tavolo.
        </div>

        <div className="px-3 py-2.5 bg-bg-surface border border-border rounded-md text-xs leading-snug mb-3">
          <strong className="text-text-primary">Sopravvalutare:</strong> un prezzo gonfiato tiene la casa mesi sul mercato.
          L'<em>effetto prime 2 settimane</em> e reale: gli immobili prezzati correttamente fin dall'inizio
          ottengono il 94% del prezzo richiesto. Quelli sovraprezzati che restano mesi sul mercato
          scendono al 90% &mdash; meno di quanto avresti ottenuto partendo dal prezzo giusto.
        </div>

        <p className="mt-2 px-2.5 py-2 bg-success-muted border border-success/30 rounded text-xs leading-snug text-success">
          Il prezzo corretto non e ne il piu alto ne il piu basso: e quello supportato dai dati
          e che permette una vendita in tempi ragionevoli, al giusto valore.
        </p>
      </InsightCard>

      <InsightCard title="Il valore di un buon agente immobiliare" icon={"\u2B50"}>
        <p className="mb-2">
          Un agente immobiliare competente e un <strong className="text-text-primary">professionista</strong> che
          porta valore reale alla vendita. La sua commissione si giustifica quando il lavoro e concreto:
        </p>
        <div className="flex flex-col gap-2 mt-2">
          <div className="px-2.5 py-2 bg-success-muted border border-success/30 rounded text-[0.78rem] leading-snug">
            <strong className="text-success">Presentazione dell'immobile</strong>
            <p className="text-text-secondary mt-0.5">Sa quali lavori conviene fare prima della vendita, come valorizzare gli spazi, quali difetti correggere e quali lasciare. L'esperienza conta.</p>
          </div>
          <div className="px-2.5 py-2 bg-success-muted border border-success/30 rounded text-[0.78rem] leading-snug">
            <strong className="text-success">Home staging e fotografia</strong>
            <p className="text-text-secondary mt-0.5">Piccoli investimenti (500-2.000 EUR) che rendono 5-10x. Spostare un mobile, una mano di vernice, foto professionali fanno la differenza tra una visita e un'offerta.</p>
          </div>
          <div className="px-2.5 py-2 bg-success-muted border border-success/30 rounded text-[0.78rem] leading-snug">
            <strong className="text-success">Negoziazione professionale</strong>
            <p className="text-text-secondary mt-0.5">Un agente esperto ottiene il 5-10% in piu attraverso tecniche di negoziazione. Spesso il costo della commissione si ripaga da solo.</p>
          </div>
          <div className="px-2.5 py-2 bg-success-muted border border-success/30 rounded text-[0.78rem] leading-snug">
            <strong className="text-success">Qualificazione acquirenti</strong>
            <p className="text-text-secondary mt-0.5">Filtra i perditempo, verifica la pre-approvazione del mutuo, riduce il rischio di trattative che saltano all'ultimo.</p>
          </div>
          <div className="px-2.5 py-2 bg-success-muted border border-success/30 rounded text-[0.78rem] leading-snug">
            <strong className="text-success">Strategia di prezzo</strong>
            <p className="text-text-secondary mt-0.5">
              Conosce il mercato locale, sa quale prezzo attira le offerte giuste e quale le allontana.
              La differenza tra vendere in 3 settimane e restare 6 mesi sul mercato.
            </p>
          </div>
        </div>
        <p className="mt-3 px-2.5 py-2 bg-accent-muted border border-accent/30 rounded text-xs leading-snug text-accent">
          Un buon professionista merita di essere pagato equamente per il suo lavoro.
          L'obiettivo e trovare il giusto equilibrio: compenso proporzionato al valore creato,
          tempi ragionevoli, risultato che soddisfi tutti.
        </p>
      </InsightCard>

      <InsightCard title="Come collaborare con un agente" icon="🤝">
        <ol className="my-1.5 pl-5 text-xs leading-relaxed list-decimal">
          <li>
            <strong className="text-text-primary">Condividi i dati OMI</strong>
            <p className="mt-0.5 mb-2 text-text-tertiary text-[0.78rem]">
              Presenta la tua ricerca: "questi sono i range OMI per la nostra zona". Un buon agente apprezzerà
              un cliente informato e vi confronterete sui numeri.
            </p>
          </li>
          <li>
            <strong className="text-text-primary">Confronta: ottieni almeno 3 valutazioni</strong>
            <p className="mt-0.5 mb-2 text-text-tertiary text-[0.78rem]">
              Diffida sia della piu bassa (potrebbe voler chiudere in fretta) che della piu alta (potrebbe volere il mandato).
              La valutazione giusta e quella documentata con dati reali.
            </p>
          </li>
          <li>
            <strong className="text-text-primary">Concordate obiettivi realistici</strong>
            <p className="mt-0.5 mb-2 text-text-tertiary text-[0.78rem]">
              Prezzo obiettivo, tempi di vendita, strategia di marketing. Quando venditore e agente condividono
              aspettative realistiche, il risultato e migliore per tutti.
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
