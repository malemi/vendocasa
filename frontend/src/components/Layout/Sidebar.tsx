import { Link } from "react-router-dom";

interface SidebarProps {
  children: React.ReactNode;
}

export function Sidebar({ children }: SidebarProps) {
  return (
    <aside className="w-[420px] h-full flex flex-col bg-bg-elevated border-r border-border shrink-0">
      <div className="flex-1 overflow-auto flex flex-col">
        {children}
      </div>
      <div className="px-4 py-2 border-t border-border text-center text-xs text-text-tertiary shrink-0">
        <Link to="/privacy" className="text-text-tertiary hover:text-text-secondary transition-colors no-underline">
          Privacy
        </Link>
        <span className="mx-1.5 text-border">|</span>
        <Link to="/terms" className="text-text-tertiary hover:text-text-secondary transition-colors no-underline">
          Termini
        </Link>
      </div>
    </aside>
  );
}
