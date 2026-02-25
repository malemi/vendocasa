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

  return (
    <div style={styles.container}>
      <h4 style={styles.heading}>Aggiungi transazione</h4>
      <form onSubmit={handleSubmit} style={styles.form}>
        <div style={styles.row}>
          <div style={styles.field}>
            <label style={styles.label}>Data (YYYY-MM-DD)</label>
            <input
              type="date"
              value={form.transaction_date || ""}
              onChange={(e) => handleChange("transaction_date", e.target.value)}
              style={styles.input}
            />
          </div>
          <div style={styles.field}>
            <label style={styles.label}>Tipo</label>
            <select
              value={form.transaction_type || ""}
              onChange={(e) => handleChange("transaction_type", e.target.value)}
              style={styles.input}
            >
              <option value="Residenziale">Residenziale</option>
              <option value="Commerciale">Commerciale</option>
              <option value="Produttivo">Produttivo</option>
              <option value="Terziario">Terziario</option>
            </select>
          </div>
        </div>

        <div style={styles.field}>
          <label style={styles.label}>Prezzo dichiarato (EUR)</label>
          <input
            type="number"
            value={form.declared_price || ""}
            onChange={(e) => handleChange("declared_price", e.target.value)}
            placeholder="250000"
            style={styles.input}
          />
        </div>

        <div style={styles.row}>
          <div style={styles.field}>
            <label style={styles.label}>Categoria catastale</label>
            <input
              type="text"
              value={form.cadastral_category || ""}
              onChange={(e) => handleChange("cadastral_category", e.target.value)}
              placeholder="A/2"
              style={styles.input}
            />
          </div>
          <div style={styles.field}>
            <label style={styles.label}>Vani</label>
            <input
              type="number"
              step="0.5"
              value={form.cadastral_vani || ""}
              onChange={(e) => handleChange("cadastral_vani", e.target.value)}
              style={styles.input}
            />
          </div>
          <div style={styles.field}>
            <label style={styles.label}>m2</label>
            <input
              type="number"
              value={form.cadastral_mq || ""}
              onChange={(e) => handleChange("cadastral_mq", e.target.value)}
              style={styles.input}
            />
          </div>
        </div>

        <div style={styles.field}>
          <label style={styles.label}>Note</label>
          <textarea
            value={form.notes || ""}
            onChange={(e) => handleChange("notes", e.target.value)}
            rows={2}
            style={{ ...styles.input, resize: "vertical" }}
          />
        </div>

        <button type="submit" disabled={saving} style={styles.button}>
          {saving ? "Salvataggio..." : "Salva transazione"}
        </button>

        {message && <p style={styles.message}>{message}</p>}
      </form>
    </div>
  );
}

const styles = {
  container: {
    backgroundColor: "white",
    borderRadius: "8px",
    padding: "12px",
    border: "1px solid #e2e8f0",
  } as React.CSSProperties,
  heading: {
    margin: "0 0 12px",
    fontSize: "0.85rem",
    color: "#4a5568",
    fontWeight: 600,
  } as React.CSSProperties,
  form: {
    display: "flex",
    flexDirection: "column",
    gap: "10px",
  } as React.CSSProperties,
  row: {
    display: "flex",
    gap: "8px",
  } as React.CSSProperties,
  field: {
    display: "flex",
    flexDirection: "column",
    gap: "3px",
    flex: 1,
  } as React.CSSProperties,
  label: {
    fontSize: "0.7rem",
    fontWeight: 600,
    color: "#718096",
    textTransform: "uppercase",
  } as React.CSSProperties,
  input: {
    padding: "6px 8px",
    border: "1px solid #cbd5e0",
    borderRadius: "4px",
    fontSize: "0.85rem",
  } as React.CSSProperties,
  button: {
    padding: "8px",
    backgroundColor: "#48bb78",
    color: "white",
    border: "none",
    borderRadius: "4px",
    fontSize: "0.85rem",
    fontWeight: 600,
    cursor: "pointer",
  } as React.CSSProperties,
  message: {
    margin: 0,
    fontSize: "0.8rem",
    color: "#4a5568",
  } as React.CSSProperties,
};
