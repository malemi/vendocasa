import type { QuotationItem } from "../../types";

interface QuotationTableProps {
  quotations: QuotationItem[];
}

export function QuotationTable({ quotations }: QuotationTableProps) {
  if (quotations.length === 0) {
    return <p style={{ color: "#a0aec0", fontSize: "0.85rem" }}>Nessuna quotazione disponibile</p>;
  }

  return (
    <div style={styles.container}>
      <h4 style={styles.heading}>Quotazioni OMI</h4>
      <table style={styles.table}>
        <thead>
          <tr>
            <th style={styles.th}>Stato conserv.</th>
            <th style={styles.th}>EUR/m2 min</th>
            <th style={styles.th}>EUR/m2 max</th>
            <th style={styles.th}>Sup.</th>
            <th style={styles.th}>Affitto min</th>
            <th style={styles.th}>Affitto max</th>
          </tr>
        </thead>
        <tbody>
          {quotations.map((q, i) => (
            <tr key={i} style={q.is_prevalent ? styles.prevalentRow : undefined}>
              <td style={styles.td}>
                {q.conservation_state}
                {q.is_prevalent && <span style={styles.prevBadge}>P</span>}
              </td>
              <td style={styles.tdNum}>{q.price_min?.toLocaleString("it-IT")}</td>
              <td style={styles.tdNum}>{q.price_max?.toLocaleString("it-IT")}</td>
              <td style={styles.td}>{q.surface_type_sale}</td>
              <td style={styles.tdNum}>{q.rent_min?.toLocaleString("it-IT")}</td>
              <td style={styles.tdNum}>{q.rent_max?.toLocaleString("it-IT")}</td>
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
  prevalentRow: {
    backgroundColor: "#fffff0",
  } as React.CSSProperties,
  prevBadge: {
    marginLeft: "6px",
    padding: "1px 5px",
    backgroundColor: "#fefcbf",
    color: "#975a16",
    borderRadius: "4px",
    fontSize: "0.65rem",
    fontWeight: 700,
  } as React.CSSProperties,
};
