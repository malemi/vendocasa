import { Link } from "react-router-dom";

interface SidebarProps {
  children: React.ReactNode;
}

export function Sidebar({ children }: SidebarProps) {
  return (
    <aside style={styles.sidebar}>
      <div style={styles.main}>{children}</div>
      <div style={styles.footer}>
        <Link to="/privacy" style={styles.footerLink}>
          Privacy
        </Link>
        <span style={styles.separator}>|</span>
        <Link to="/terms" style={styles.footerLink}>
          Termini
        </Link>
      </div>
    </aside>
  );
}

const styles = {
  sidebar: {
    width: "420px",
    height: "100%",
    display: "flex",
    flexDirection: "column",
    backgroundColor: "#f7fafc",
    borderRight: "1px solid #e2e8f0",
  } as React.CSSProperties,
  main: {
    flex: 1,
    overflow: "auto",
    display: "flex",
    flexDirection: "column",
  } as React.CSSProperties,
  footer: {
    padding: "8px 16px",
    borderTop: "1px solid #e2e8f0",
    textAlign: "center",
    fontSize: "12px",
    color: "#a0aec0",
    flexShrink: 0,
  } as React.CSSProperties,
  footerLink: {
    color: "#a0aec0",
    textDecoration: "none",
  } as React.CSSProperties,
  separator: {
    margin: "0 6px",
    color: "#cbd5e0",
  } as React.CSSProperties,
};
