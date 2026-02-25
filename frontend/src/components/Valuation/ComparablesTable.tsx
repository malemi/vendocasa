import type { ComparableItem } from "../../types";

interface ComparablesTableProps {
  comparables: ComparableItem[];
}

export function ComparablesTable({ comparables }: ComparablesTableProps) {
  if (comparables.length === 0) {
    return (
      <p style={{ color: "#a0aec0", fontSize: "0.85rem" }}>
        Nessuna transazione comparabile registrata
      </p>
    );
  }

  return (
    <div style={styles.container}>
      <h4 style={styles.heading}>Transazioni comparabili</h4>
      <table style={styles.table}>
        <thead>
          <tr>
            <th style={styles.th}>Data</th>
            <th style={styles.th}>Prezzo</th>
            <th style={styles.th}>Cat.</th>
            <th style={styles.th}>Consist.</th>
            <th style={styles.th}>Note</th>
          </tr>
        </thead>
        <tbody>
          {comparables.map((c, i) => (
            <tr key={i}>
              <td style={styles.td}>{c.transaction_date || "-"}</td>
              <td style={styles.tdNum}>
                {c.declared_price
                  ? new Intl.NumberFormat("it-IT", {
                      style: "currency",
                      currency: "EUR",
                      maximumFractionDigits: 0,
                    }).format(c.declared_price)
                  : "-"}
              </td>
              <td style={styles.td}>{c.cadastral_category || "-"}</td>
              <td style={styles.tdNum}>
                {c.cadastral_mq
                  ? `${c.cadastral_mq} m2`
                  : c.cadastral_vani
                    ? `${c.cadastral_vani} vani`
                    : "-"}
              </td>
              <td style={styles.td}>
                {c.notes ? (c.notes.length > 40 ? c.notes.slice(0, 40) + "..." : c.notes) : "-"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
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
    margin: "0 0 8px",
    fontSize: "0.85rem",
    color: "#4a5568",
    fontWeight: 600,
  } as React.CSSProperties,
  table: {
    width: "100%",
    borderCollapse: "collapse",
    fontSize: "0.8rem",
  } as React.CSSProperties,
  th: {
    textAlign: "left",
    padding: "6px 8px",
    borderBottom: "2px solid #e2e8f0",
    color: "#718096",
    fontWeight: 600,
    fontSize: "0.7rem",
    textTransform: "uppercase",
  } as React.CSSProperties,
  td: {
    padding: "6px 8px",
    borderBottom: "1px solid #edf2f7",
  } as React.CSSProperties,
  tdNum: {
    padding: "6px 8px",
    borderBottom: "1px solid #edf2f7",
    textAlign: "right",
    fontVariantNumeric: "tabular-nums",
  } as React.CSSProperties,
};
