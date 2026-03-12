import { useState } from "react";
import { Button } from "../ui/Button";

interface FreakonomicsSectionProps {
  onOpenApp: () => void;
}

export function FreakonomicsSection({ onOpenApp }: FreakonomicsSectionProps) {
  const [salePrice, setSalePrice] = useState(250000);

  const underPrice = 20000;
  const overPrice = 30000;
  const correctPrice = salePrice;
  const tooLow = salePrice - underPrice;
  const tooHigh = salePrice + overPrice;

  return (
    <section className="py-24 px-6 relative">
      {/* Subtle tinted background */}
      <div className="absolute inset-0 bg-gradient-to-b from-accent-muted/50 via-bg-primary to-bg-primary pointer-events-none" />

      <div className="relative z-10 max-w-6xl mx-auto">
        <div className="text-center mb-16">
          <span className="inline-block px-4 py-1.5 rounded-full bg-accent-muted text-accent text-sm font-semibold mb-6">
            Il valore reale
          </span>
          <h2 className="text-3xl md:text-5xl font-bold mb-4">
            Il prezzo giusto
            <br />
            <span className="text-accent">conviene a tutti</span>
          </h2>
          <p className="text-text-secondary max-w-2xl mx-auto">
            Venditori, acquirenti e professionisti: obiettivi realistici fanno vincere tutti
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-start">
          {/* Left: text content */}
          <div className="space-y-6">
            <div className="p-6 rounded-2xl bg-bg-elevated border border-border">
              <p className="text-text-primary leading-relaxed text-lg">
                <span className="font-semibold text-danger">Non svendere.</span>{" "}
                Chi vende casa senza conoscere il valore reale del proprio immobile
                rischia di accettare offerte al ribasso. Parti dai{" "}
                <span className="font-semibold text-accent">dati ufficiali OMI</span>{" "}
                per sapere quanto vale davvero.
              </p>
            </div>

            <div className="p-6 rounded-2xl bg-bg-elevated border border-border">
              <p className="text-text-primary leading-relaxed text-lg">
                <span className="font-semibold text-danger">Non sopravvalutare.</span>{" "}
                Un prezzo gonfiato tiene la casa{" "}
                <span className="font-semibold text-teal">mesi sul mercato</span>{" "}
                e alla fine vendi a meno. Gli immobili prezzati correttamente
                fin dall'inizio ottengono il{" "}
                <span className="font-semibold text-teal">94% del prezzo richiesto</span>.
              </p>
            </div>

            <div className="flex items-start gap-3 p-4 rounded-xl bg-success-muted/50 border border-success/20">
              <span className="text-2xl mt-0.5">💡</span>
              <p className="text-sm text-text-secondary leading-relaxed">
                <strong className="text-text-primary">Prezzo corretto + professionista motivato = vendita al giusto prezzo.</strong>{" "}
                L'agente immobiliare sa come presentare la casa, quali lavori fare, come negoziare.
                Con obiettivi realistici, vincono tutti: chi compra, chi vende e chi lavora.
              </p>
            </div>
          </div>

          {/* Right: interactive calculator */}
          <div className="p-8 rounded-2xl bg-bg-elevated border border-border">
            <h3 className="text-lg font-semibold mb-6 text-text-primary">
              L'effetto del prezzo sulla vendita
            </h3>

            {/* Sale price slider */}
            <div className="mb-6">
              <label className="flex justify-between text-sm mb-2">
                <span className="text-text-secondary">Valore reale stimato</span>
                <span className="font-mono font-semibold text-text-primary">
                  {correctPrice.toLocaleString("it-IT")} EUR
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

            {/* Results */}
            <div className="space-y-4">
              {/* Too low */}
              <div className="p-4 rounded-xl bg-danger-muted/50 border border-danger/20">
                <div className="flex justify-between items-center mb-1">
                  <span className="text-sm text-text-secondary">Sottovalutato</span>
                  <span className="text-lg font-bold font-mono text-danger">
                    {tooLow.toLocaleString("it-IT")} EUR
                  </span>
                </div>
                <p className="text-xs text-text-tertiary">
                  Vendi in fretta ma lasci {underPrice.toLocaleString("it-IT")} EUR sul tavolo
                </p>
              </div>

              {/* Correct */}
              <div className="p-4 rounded-xl bg-success-muted/50 border border-success/20">
                <div className="flex justify-between items-center mb-1">
                  <span className="text-sm font-semibold text-success">Prezzo corretto</span>
                  <span className="text-lg font-bold font-mono text-success">
                    {correctPrice.toLocaleString("it-IT")} EUR
                  </span>
                </div>
                <p className="text-xs text-text-tertiary">
                  Vendita in tempi ragionevoli, tutti soddisfatti
                </p>
              </div>

              {/* Too high */}
              <div className="p-4 rounded-xl bg-bg-surface border border-border">
                <div className="flex justify-between items-center mb-1">
                  <span className="text-sm text-text-secondary">Sopravvalutato</span>
                  <span className="text-lg font-bold font-mono text-text-tertiary">
                    {tooHigh.toLocaleString("it-IT")} EUR
                  </span>
                </div>
                <p className="text-xs text-text-tertiary">
                  Mesi sul mercato, poi costretto a ribassare sotto il valore reale
                </p>
              </div>

              <div className="text-center pt-4 border-t border-border">
                <p className="text-sm text-text-secondary">
                  L'<em>effetto prime 2 settimane</em>: chi parte dal prezzo giusto
                  vende meglio di chi parte alto e poi scende.
                </p>
              </div>
            </div>

            <Button
              variant="primary"
              fullWidth
              className="mt-8"
              onClick={onOpenApp}
            >
              Scopri il valore reale del tuo immobile
            </Button>
          </div>
        </div>
      </div>
    </section>
  );
}
