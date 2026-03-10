import { useState } from "react";
import { createTransaction } from "../../api/client";
import type { TransactionInput } from "../../types";

interface TransactionFormProps {
  defaultLinkZona?: string;
  defaultZoneCode?: string;
  defaultMunicipality?: string;
  onCreated?: () => void;
}

export function TransactionForm({
  defaultLinkZona,
  defaultZoneCode,
  defaultMunicipality,
  onCreated,
}: TransactionFormProps) {
  const [form, setForm] = useState<TransactionInput>({
    link_zona: defaultLinkZona || "",
    omi_zone: defaultZoneCode || "",
    municipality: defaultMunicipality || "",
    transaction_type: "Residenziale",
  });
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  const handleChange = (field: string, value: string | number) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setMessage("");
    try {
      const input: TransactionInput = {
        ...form,
        declared_price: form.declared_price ? Number(form.declared_price) : undefined,
        cadastral_vani: form.cadastral_vani ? Number(form.cadastral_vani) : undefined,
        cadastral_mq: form.cadastral_mq ? Number(form.cadastral_mq) : undefined,
      };
      await createTransaction(input);
      setMessage("Transazione salvata");
      onCreated?.();
    } catch {
      setMessage("Errore nel salvataggio");
    } finally {
      setSaving(false);
    }
  };

  const inputClasses =
    "px-2 py-1.5 border border-border rounded bg-bg-surface text-text-primary text-[0.85rem] outline-none placeholder:text-text-tertiary focus:border-accent/50 focus:ring-1 focus:ring-accent/20 transition-colors";

  return (
    <div className="bg-bg-elevated rounded-lg p-3 border border-border">
      <h4 className="m-0 mb-3 text-[0.85rem] text-text-secondary font-semibold">
        Aggiungi transazione
      </h4>
      <form onSubmit={handleSubmit} className="flex flex-col gap-2.5">
        <div className="flex gap-2">
          <div className="flex flex-col gap-0.5 flex-1">
            <label className="text-[0.7rem] font-semibold text-text-tertiary uppercase">
              Data (YYYY-MM-DD)
            </label>
            <input
              type="date"
              value={form.transaction_date || ""}
              onChange={(e) => handleChange("transaction_date", e.target.value)}
              className={inputClasses}
            />
          </div>
          <div className="flex flex-col gap-0.5 flex-1">
            <label className="text-[0.7rem] font-semibold text-text-tertiary uppercase">
              Tipo
            </label>
            <select
              value={form.transaction_type || ""}
              onChange={(e) => handleChange("transaction_type", e.target.value)}
              className={inputClasses}
            >
              <option value="Residenziale">Residenziale</option>
              <option value="Commerciale">Commerciale</option>
              <option value="Produttivo">Produttivo</option>
              <option value="Terziario">Terziario</option>
            </select>
          </div>
        </div>

        <div className="flex flex-col gap-0.5">
          <label className="text-[0.7rem] font-semibold text-text-tertiary uppercase">
            Prezzo dichiarato (EUR)
          </label>
          <input
            type="number"
            value={form.declared_price || ""}
            onChange={(e) => handleChange("declared_price", e.target.value)}
            placeholder="250000"
            className={inputClasses}
          />
        </div>

        <div className="flex gap-2">
          <div className="flex flex-col gap-0.5 flex-1">
            <label className="text-[0.7rem] font-semibold text-text-tertiary uppercase">
              Categoria catastale
            </label>
            <input
              type="text"
              value={form.cadastral_category || ""}
              onChange={(e) => handleChange("cadastral_category", e.target.value)}
              placeholder="A/2"
              className={inputClasses}
            />
          </div>
          <div className="flex flex-col gap-0.5 flex-1">
            <label className="text-[0.7rem] font-semibold text-text-tertiary uppercase">
              Vani
            </label>
            <input
              type="number"
              step="0.5"
              value={form.cadastral_vani || ""}
              onChange={(e) => handleChange("cadastral_vani", e.target.value)}
              className={inputClasses}
            />
          </div>
          <div className="flex flex-col gap-0.5 flex-1">
            <label className="text-[0.7rem] font-semibold text-text-tertiary uppercase">
              m2
            </label>
            <input
              type="number"
              value={form.cadastral_mq || ""}
              onChange={(e) => handleChange("cadastral_mq", e.target.value)}
              className={inputClasses}
            />
          </div>
        </div>

        <div className="flex flex-col gap-0.5">
          <label className="text-[0.7rem] font-semibold text-text-tertiary uppercase">
            Note
          </label>
          <textarea
            value={form.notes || ""}
            onChange={(e) => handleChange("notes", e.target.value)}
            rows={2}
            className={`${inputClasses} resize-y`}
          />
        </div>

        <button
          type="submit"
          disabled={saving}
          className="px-2 py-2 bg-success text-white border-none rounded text-[0.85rem] font-semibold cursor-pointer hover:bg-success/80 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {saving ? "Salvataggio..." : "Salva transazione"}
        </button>

        {message && (
          <p className="m-0 text-[0.8rem] text-text-secondary">{message}</p>
        )}
      </form>
    </div>
  );
}
