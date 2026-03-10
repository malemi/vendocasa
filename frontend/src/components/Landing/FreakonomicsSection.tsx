import { useState } from "react";
import { Button } from "../ui/Button";

interface FreakonomicsSectionProps {
  onOpenApp: () => void;
}

export function FreakonomicsSection({ onOpenApp }: FreakonomicsSectionProps) {
  const [salePrice, setSalePrice] = useState(250000);
  const [discount, setDiscount] = useState(10000);

  const commissionRate = 0.03;
  const yourLoss = discount;
  const agentLoss = discount * commissionRate;

  return (
    <section className="py-24 px-6 relative">
      {/* Subtle tinted background */}
      <div className="absolute inset-0 bg-gradient-to-b from-accent-muted/50 via-bg-primary to-bg-primary pointer-events-none" />

      <div className="relative z-10 max-w-6xl mx-auto">
        <div className="text-center mb-16">
          <span className="inline-block px-4 py-1.5 rounded-full bg-danger-muted text-danger text-sm font-semibold mb-6">
            Lo sapevi?
          </span>
          <h2 className="text-3xl md:text-5xl font-bold mb-4">
            Il problema che nessun agente
            <br />
            <span className="text-accent">ti racconta</span>
          </h2>
          <p className="text-text-secondary max-w-2xl mx-auto">
            Basato sullo studio Levitt & Syverson, reso celebre dal libro Freakonomics
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-start">
          {/* Left: text content */}
          <div className="space-y-6">
            <div className="p-6 rounded-2xl bg-bg-elevated border border-border">
              <p className="text-text-primary leading-relaxed text-lg">
                Quando un agente immobiliare vende la{" "}
                <span className="font-semibold text-accent">propria</span> casa,
                la tiene sul mercato{" "}
                <span className="font-semibold text-teal">10 giorni in piu</span>{" "}
                e la vende al{" "}
                <span className="font-semibold text-teal">3-10% in piu</span>.
              </p>
            </div>

            <div className="p-6 rounded-2xl bg-bg-elevated border border-border">
              <p className="text-text-primary leading-relaxed text-lg">
                Quando vende la{" "}
                <span className="font-semibold text-danger">tua</span>?
                Chiude in fretta. Perche la sua commissione e quasi uguale
                sia che tu venda a prezzo pieno, sia che svendi.
              </p>
            </div>

            <div className="flex items-start gap-3 p-4 rounded-xl bg-danger-muted/50 border border-danger/20">
              <span className="text-2xl mt-0.5">💡</span>
              <p className="text-sm text-text-secondary leading-relaxed">
                L'incentivo dell'agente e chiudere <strong className="text-text-primary">tante</strong> vendite velocemente,
                non ottenere il <strong className="text-text-primary">miglior prezzo</strong> per te.
                Volume batte valore.
              </p>
            </div>
          </div>

          {/* Right: interactive calculator */}
          <div className="p-8 rounded-2xl bg-bg-elevated border border-border">
            <h3 className="text-lg font-semibold mb-6 text-text-primary">
              Fai i conti tu stesso
            </h3>

            {/* Sale price slider */}
            <div className="mb-6">
              <label className="flex justify-between text-sm mb-2">
                <span className="text-text-secondary">Prezzo di vendita</span>
                <span className="font-mono font-semibold text-text-primary">
                  {salePrice.toLocaleString("it-IT")} EUR
                </span>
              </label>
              <input
                type="range"
                min={100000}
                max={800000}
                step={10000}
                value={salePrice}
                onChange={(e) => setSalePrice(Number(e.target.value))}
                className="w-full accent-accent h-2 rounded-full bg-bg-surface appearance-none cursor-pointer
                  [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-5 [&::-webkit-slider-thumb]:h-5
                  [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-accent [&::-webkit-slider-thumb]:cursor-pointer
                  [&::-webkit-slider-thumb]:shadow-[0_0_10px_rgba(247,166,0,0.4)]"
              />
            </div>

            {/* Discount slider */}
            <div className="mb-8">
              <label className="flex justify-between text-sm mb-2">
                <span className="text-text-secondary">Sconto accettato</span>
                <span className="font-mono font-semibold text-danger">
                  -{discount.toLocaleString("it-IT")} EUR
                </span>
              </label>
              <input
                type="range"
                min={5000}
                max={50000}
                step={1000}
                value={discount}
                onChange={(e) => setDiscount(Number(e.target.value))}
                className="w-full accent-danger h-2 rounded-full bg-bg-surface appearance-none cursor-pointer
                  [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-5 [&::-webkit-slider-thumb]:h-5
                  [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-danger [&::-webkit-slider-thumb]:cursor-pointer
                  [&::-webkit-slider-thumb]:shadow-[0_0_10px_rgba(245,101,101,0.4)]"
              />
            </div>

            {/* Results */}
            <div className="space-y-4">
              <div className="flex justify-between items-center p-4 rounded-xl bg-danger-muted/50 border border-danger/20">
                <span className="text-sm text-text-secondary">Tu perdi</span>
                <span className="text-2xl font-bold font-mono text-danger">
                  {yourLoss.toLocaleString("it-IT")} EUR
                </span>
              </div>

              <div className="flex justify-between items-center p-4 rounded-xl bg-bg-surface border border-border">
                <span className="text-sm text-text-secondary">L'agente perde</span>
                <span className="text-2xl font-bold font-mono text-text-tertiary">
                  {agentLoss.toLocaleString("it-IT")} EUR
                </span>
              </div>

              <div className="text-center pt-4 border-t border-border">
                <p className="text-sm text-text-tertiary mb-1">
                  Con una commissione del {(commissionRate * 100).toFixed(0)}%
                </p>
                <p className="text-text-secondary">
                  Per l'agente, il tuo sconto di{" "}
                  <strong className="text-danger">{yourLoss.toLocaleString("it-IT")} EUR</strong>{" "}
                  vale solo{" "}
                  <strong className="text-text-tertiary">{agentLoss.toLocaleString("it-IT")} EUR</strong>.
                </p>
              </div>
            </div>

            <Button
              variant="primary"
              fullWidth
              className="mt-8"
              onClick={onOpenApp}
            >
              Scopri quanto vale davvero
            </Button>
          </div>
        </div>
      </div>
    </section>
  );
}
