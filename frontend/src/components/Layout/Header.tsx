export function Header() {
  return (
    <header style={styles.header}>
      <h1 style={styles.title}>VendoCasa</h1>
      <span style={styles.subtitle}>Valutazione Immobiliare OMI</span>
    </header>
  );
}

const styles = {
  header: {
    display: "flex",
    alignItems: "center",
    gap: "16px",
    padding: "12px 24px",
    backgroundColor: "#1a365d",
    color: "white",
    boxShadow: "0 2px 4px rgba(0,0,0,0.1)",
  } as React.CSSProperties,
  title: {
    margin: 0,
    fontSize: "1.5rem",
    fontWeight: 700,
  } as React.CSSProperties,
  subtitle: {
    fontSize: "0.9rem",
    opacity: 0.8,
  } as React.CSSProperties,
};
