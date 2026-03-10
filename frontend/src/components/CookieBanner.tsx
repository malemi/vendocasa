import { useState } from "react";

interface CookieBannerProps {
  onAccept: () => void;
  onDecline?: () => void;
}

export function CookieBanner({ onAccept, onDecline }: CookieBannerProps) {
  const [declined, setDeclined] = useState(false);

  const handleDecline = () => {
    setDeclined(true);
  };

  const handleBack = () => {
    setDeclined(false);
    onDecline?.();
  };

  if (declined) {
    return (
      <div className="fixed inset-0 z-[10000] flex items-center justify-center bg-black/60 backdrop-blur-sm">
        <div className="bg-bg-elevated rounded-xl p-8 max-w-[500px] w-[90%] shadow-2xl text-center border border-border">
          <p className="text-[15px] leading-[1.7] text-text-secondary italic mb-6">
            Mi spiace, per motivi di sicurezza questo servizio non pu&ograve;
            funzionare senza il settaggio di cookie. Capiamo perfettamente le
            sue preferenze, ma non possiamo continuare. Arrivederci.
          </p>
          <button
            onClick={handleBack}
            className="bg-transparent border-none text-accent cursor-pointer text-sm underline p-0 hover:text-accent-hover transition-colors"
          >
            &larr; Torna indietro
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-[10000] flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-bg-elevated rounded-xl px-10 py-8 max-w-[500px] w-[90%] shadow-2xl text-center border border-border">
        <h2 className="m-0 mb-4 text-xl font-semibold text-text-primary">
          Cookie e Privacy
        </h2>
        <p className="text-sm leading-relaxed text-text-secondary mb-6">
          Questo sito utilizza cookie tecnici per il funzionamento del servizio
          e per identificare eventuali abusi. Proseguendo, accetti l'utilizzo
          dei cookie come descritto nella nostra{" "}
          <a href="/privacy" className="text-accent underline hover:text-accent-hover transition-colors">
            Informativa Privacy
          </a>{" "}
          e nei{" "}
          <a href="/terms" className="text-accent underline hover:text-accent-hover transition-colors">
            Termini di Utilizzo
          </a>
          .
        </p>
        <div className="flex gap-3 justify-center">
          <button
            onClick={onAccept}
            className="px-8 py-2.5 text-sm font-semibold text-bg-primary bg-accent border-none rounded-lg cursor-pointer hover:bg-accent-hover transition-colors"
          >
            Accetto
          </button>
          <button
            onClick={handleDecline}
            className="px-8 py-2.5 text-sm font-semibold text-text-secondary bg-bg-surface border border-border rounded-lg cursor-pointer hover:bg-bg-primary hover:text-text-primary transition-colors"
          >
            Rifiuto
          </button>
        </div>
      </div>
    </div>
  );
}
