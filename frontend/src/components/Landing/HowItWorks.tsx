const steps = [
  {
    number: "01",
    icon: (
      <svg viewBox="0 0 48 48" fill="none" className="w-12 h-12">
        <circle cx="24" cy="20" r="8" stroke="var(--color-accent)" strokeWidth="2.5" fill="none" />
        <path d="M24 30c-8 0-14 4-14 8v2h28v-2c0-4-6-8-14-8z" stroke="var(--color-accent)" strokeWidth="2.5" fill="var(--color-accent-muted)" />
        <path d="M36 14l-4 4m4-4v4m0-4h-4" stroke="var(--color-teal)" strokeWidth="2" strokeLinecap="round" />
      </svg>
    ),
    title: "Dimmi dove",
    description:
      "Inserisci l'indirizzo e il tipo di immobile. Il nostro sistema lo localizza sulla mappa catastale OMI e trova la zona di appartenenza.",
  },
  {
    number: "02",
    icon: (
      <svg viewBox="0 0 48 48" fill="none" className="w-12 h-12">
        <rect x="8" y="8" width="32" height="32" rx="4" stroke="var(--color-accent)" strokeWidth="2.5" fill="none" />
        <path d="M16 20h16M16 28h10" stroke="var(--color-accent)" strokeWidth="2.5" strokeLinecap="round" />
        <circle cx="36" cy="36" r="8" fill="var(--color-teal)" opacity="0.2" />
        <path d="M33 36h6m-3-3v6" stroke="var(--color-teal)" strokeWidth="2" strokeLinecap="round" />
      </svg>
    ),
    title: "Descrivi il tuo immobile",
    description:
      "Piano, stato conservativo, esposizione, classe energetica. Ogni dettaglio affina la stima con coefficienti reali.",
  },
  {
    number: "03",
    icon: (
      <svg viewBox="0 0 48 48" fill="none" className="w-12 h-12">
        <path d="M8 36l8-12 6 6 8-14 10 8" stroke="var(--color-accent)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" fill="none" />
        <circle cx="40" cy="24" r="4" fill="var(--color-success)" opacity="0.3" />
        <path d="M38 24l2 2 4-4" stroke="var(--color-success)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        <text x="6" y="46" fill="var(--color-accent)" fontSize="10" fontFamily="var(--font-mono)" fontWeight="600">EUR</text>
      </svg>
    ),
    title: "Ricevi la valutazione",
    description:
      "Range di prezzo basato sui dati OMI, corretto con i coefficienti del tuo immobile. Trasparente e documentato.",
  },
];

export function HowItWorks() {
  return (
    <section className="py-24 px-6">
      <div className="max-w-6xl mx-auto">
        <h2 className="text-3xl md:text-4xl font-bold text-center mb-4">
          Come funziona
        </h2>
        <p className="text-text-secondary text-center mb-16 max-w-2xl mx-auto">
          Tre passaggi. Due minuti. Zero sorprese.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {steps.map((step) => (
            <div
              key={step.number}
              className="
                relative p-8 rounded-2xl
                bg-bg-elevated border border-border
                hover:border-border-light hover:bg-bg-surface/30
                transition-all duration-300
                group
              "
            >
              {/* Step number */}
              <span className="absolute top-6 right-6 text-5xl font-bold text-text-tertiary/30 font-mono select-none group-hover:text-accent/20 transition-colors">
                {step.number}
              </span>

              {/* Icon */}
              <div className="mb-6">{step.icon}</div>

              {/* Title */}
              <h3 className="text-xl font-semibold mb-3 text-text-primary">
                {step.title}
              </h3>

              {/* Description */}
              <p className="text-text-secondary leading-relaxed text-sm">
                {step.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
