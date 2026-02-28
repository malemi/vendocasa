interface SidebarProps {
  children: React.ReactNode;
}

export function Sidebar({ children }: SidebarProps) {
  return <aside style={styles.sidebar}>{children}</aside>;
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
};
