import { Button } from "../ui/Button";

interface CtaSectionProps {
  onOpenApp: () => void;
}

export function CtaSection({ onOpenApp }: CtaSectionProps) {
  return (
    <section className="py-24 px-6 relative">
      {/* Ambient glow */}
      <div
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] rounded-full opacity-15 blur-[100px] pointer-events-none"
        style={{
          background:
            "radial-gradient(circle, var(--color-accent) 0%, transparent 70%)",
        }}
      />

      <div className="relative z-10 max-w-2xl mx-auto text-center">
        <h2 className="text-3xl md:text-5xl font-bold mb-4">
          Pronto a scoprire il{" "}
          <span className="text-accent">vero valore</span>?
        </h2>
        <p className="text-text-secondary text-lg mb-10">
          2 minuti. Gratis. Senza registrazione.
        </p>

        <Button size="lg" onClick={onOpenApp} className="animate-glow">
          Valuta ora
        </Button>

        <p className="text-text-tertiary text-sm mt-6">
          Basato su dati ufficiali OMI dell'Agenzia delle Entrate
        </p>
      </div>
    </section>
  );
}
