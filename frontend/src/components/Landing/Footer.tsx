import { Link } from "react-router-dom";
import { Logo } from "../ui/Logo";

export function Footer() {
  return (
    <footer className="py-12 px-6 border-t border-border">
      <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
        <div className="flex flex-col items-center md:items-start gap-2">
          <Logo size="sm" />
          <p className="text-text-tertiary text-xs">
            Dati: Agenzia delle Entrate — Osservatorio del Mercato Immobiliare
          </p>
        </div>

        <div className="flex items-center gap-6 text-sm text-text-secondary">
          <Link
            to="/privacy"
            className="hover:text-text-primary transition-colors"
          >
            Privacy
          </Link>
          <Link
            to="/terms"
            className="hover:text-text-primary transition-colors"
          >
            Termini
          </Link>
        </div>
      </div>
    </footer>
  );
}
