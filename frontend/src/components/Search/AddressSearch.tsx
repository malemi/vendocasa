import { useState } from "react";
import { PROPERTY_TYPES } from "../../types";

interface AddressSearchProps {
  onSearch: (params: {
    address: string;
    property_type: number;
    surface_m2?: number;
  }) => void;
  isLoading: boolean;
}

export function AddressSearch({ onSearch, isLoading }: AddressSearchProps) {
  const [address, setAddress] = useState("");
  const [propertyType, setPropertyType] = useState(20);
  const [surfaceM2, setSurfaceM2] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!address.trim()) return;
    onSearch({
      address: address.trim(),
      property_type: propertyType,
      surface_m2: surfaceM2 ? parseFloat(surfaceM2) : undefined,
    });
  };

  return (
    <form onSubmit={handleSubmit} style={styles.form}>
      <div style={styles.field}>
        <label style={styles.label}>Indirizzo</label>
        <input
          type="text"
          value={address}
          onChange={(e) => setAddress(e.target.value)}
          placeholder="Via Roma 1, Milano"
          style={styles.input}
        />
      </div>

      <div style={styles.row}>
        <div style={{ ...styles.field, flex: 1 }}>
          <label style={styles.label}>Tipo immobile</label>
          <select
            value={propertyType}
            onChange={(e) => setPropertyType(parseInt(e.target.value))}
            style={styles.input}
          >
            {PROPERTY_TYPES.map((pt) => (
              <option key={pt.code} value={pt.code}>
                {pt.label}
              </option>
            ))}
          </select>
        </div>

        <div style={{ ...styles.field, width: "120px" }}>
          <label style={styles.label}>Superficie m2</label>
          <input
            type="number"
            value={surfaceM2}
            onChange={(e) => setSurfaceM2(e.target.value)}
            placeholder="80"
            min="1"
            style={styles.input}
          />
        </div>
      </div>

      <button type="submit" disabled={isLoading || !address.trim()} style={styles.button}>
        {isLoading ? "Ricerca..." : "Valuta"}
      </button>
    </form>
  );
}

const styles = {
  form: {
    display: "flex",
    flexDirection: "column",
    gap: "12px",
  } as React.CSSProperties,
  field: {
    display: "flex",
    flexDirection: "column",
    gap: "4px",
  } as React.CSSProperties,
  row: {
    display: "flex",
    gap: "12px",
  } as React.CSSProperties,
  label: {
    fontSize: "0.8rem",
    fontWeight: 600,
    color: "#4a5568",
    textTransform: "uppercase",
    letterSpacing: "0.05em",
  } as React.CSSProperties,
  input: {
    padding: "8px 12px",
    border: "1px solid #cbd5e0",
    borderRadius: "6px",
    fontSize: "0.95rem",
    outline: "none",
  } as React.CSSProperties,
  button: {
    padding: "10px 16px",
    backgroundColor: "#2b6cb0",
    color: "white",
    border: "none",
    borderRadius: "6px",
    fontSize: "1rem",
    fontWeight: 600,
    cursor: "pointer",
  } as React.CSSProperties,
};
