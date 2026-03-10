const trustCards = [
  {
    icon: (
      <svg viewBox="0 0 40 40" fill="none" className="w-10 h-10">
        <rect x="4" y="4" width="32" height="32" rx="4" stroke="var(--color-teal)" strokeWidth="2" fill="var(--color-teal-muted)" />
        <path d="M12 20h16M20 12v16" stroke="var(--color-teal)" strokeWidth="2" strokeLinecap="round" />
        <circle cx="12" cy="12" r="3" fill="var(--color-teal)" opacity="0.4" />
      </svg>
    ),
    title: "Dati ufficiali OMI",
    description:
      "I range di prezzo vengono dall'Osservatorio del Mercato Immobiliare dell'Agenzia delle Entrate. Aggiornati ogni semestre su ~8.000 micro-zone italiane.",
  },
  {
    icon: (
      <svg viewBox="0 0 40 40" fill="none" className="w-10 h-10">
        <circle cx="20" cy="20" r="16" stroke="var(--color-accent)" strokeWidth="2" fill="var(--color-accent-muted)" />
        <path d="M14 20h4l2-6 4 12 2-6h4" stroke="var(--color-accent)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
    title: "AI che spiega, non che nasconde",
    description:
      "Ogni stima e accompagnata dalla spiegazione: da dove viene il range, come i coefficienti lo modificano, cosa influenza il prezzo.",
  },
  {
    icon: (
      <svg viewBox="0 0 40 40" fill="none" className="w-10 h-10">
        <path d="M20 6l14 8v12l-14 8-14-8V14l14-8z" stroke="var(--color-success)" strokeWidth="2" fill="var(--color-success-muted)" />
        <path d="M14 20l4 4 8-8" stroke="var(--color-success)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
    title: "Zero conflitti di interesse",
    description:
      "Non vendiamo case. Non prendiamo commissioni. Non abbiamo nessun incentivo a sottovalutare o sopravvalutare il tuo immobile.",
  },
];

export function TrustSection() {
  return (
    <section className="py-24 px-6">
      <div className="max-w-6xl mx-auto">
        <h2 className="text-3xl md:text-4xl font-bold text-center mb-4">
          Perche fidarti di noi
        </h2>
        <p className="text-text-secondary text-center mb-16 max-w-2xl mx-auto">
          Trasparenza radicale. Nessun secondo fine.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {trustCards.map((card) => (
            <div
              key={card.title}
              className="
                p-8 rounded-2xl
                bg-bg-elevated border border-border
                hover:border-border-light
                transition-all duration-300
              "
            >
              <div className="mb-5">{card.icon}</div>
              <h3 className="text-lg font-semibold mb-3 text-text-primary">
                {card.title}
              </h3>
              <p className="text-text-secondary leading-relaxed text-sm">
                {card.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
