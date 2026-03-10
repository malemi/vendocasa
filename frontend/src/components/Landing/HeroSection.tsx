import { Button } from "../ui/Button";
import { Logo } from "../ui/Logo";

interface HeroSectionProps {
  onOpenApp: () => void;
}

export function HeroSection({ onOpenApp }: HeroSectionProps) {
  return (
    <section className="relative min-h-screen flex flex-col items-center justify-center px-6 overflow-hidden">
      {/* Ambient glow background */}
      <div
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full opacity-20 blur-[120px] pointer-events-none"
        style={{
          background:
            "radial-gradient(circle, var(--color-accent) 0%, transparent 70%)",
        }}
      />

      {/* Navigation */}
      <nav className="absolute top-0 left-0 right-0 flex items-center justify-between px-6 py-5 md:px-12">
        <Logo size="sm" />
        <Button variant="ghost" size="sm" onClick={onOpenApp}>
          Valuta ora
        </Button>
      </nav>

      {/* Hero content */}
      <div className="relative z-10 max-w-3xl text-center animate-fade-in">
        <h1 className="text-4xl md:text-6xl lg:text-7xl font-bold tracking-tight leading-[1.1] mb-6">
          Quanto vale{" "}
          <span className="text-accent">davvero</span>
          <br />
          casa tua?
        </h1>

        <p className="text-lg md:text-xl text-text-secondary max-w-2xl mx-auto mb-10 leading-relaxed">
          Scoprilo in 2 minuti. Con i dati ufficiali OMI,
          non con le stime di un'agenzia che guadagna dalla tua fretta.
        </p>

        <div className="flex flex-col items-center gap-4">
          <Button size="lg" onClick={onOpenApp} className="animate-glow">
            Valuta ora — e gratis
          </Button>

          <p className="text-sm text-text-tertiary">
            Nessuna registrazione. Nessuna chiamata. Nessun spam.
          </p>
        </div>
      </div>

      {/* Scroll hint */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 text-text-tertiary animate-fade-in">
        <span className="text-xs tracking-widest uppercase">Scopri di piu</span>
        <svg
          className="w-5 h-5 animate-bounce"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </div>
    </section>
  );
}
