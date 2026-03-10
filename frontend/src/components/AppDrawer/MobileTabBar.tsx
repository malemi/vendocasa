interface MobileTabBarProps {
  activeTab: "chat" | "map";
  onTabChange: (tab: "chat" | "map") => void;
}

export function MobileTabBar({ activeTab, onTabChange }: MobileTabBarProps) {
  return (
    <div className="flex md:hidden border-t border-border bg-bg-primary shrink-0">
      <button
        onClick={() => onTabChange("chat")}
        className={`
          flex-1 flex items-center justify-center gap-2 py-3
          text-sm font-medium transition-colors cursor-pointer
          border-none bg-transparent
          ${activeTab === "chat" ? "text-accent" : "text-text-tertiary hover:text-text-secondary"}
        `}
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
        </svg>
        Chat
      </button>
      <button
        onClick={() => onTabChange("map")}
        className={`
          flex-1 flex items-center justify-center gap-2 py-3
          text-sm font-medium transition-colors cursor-pointer
          border-none bg-transparent
          ${activeTab === "map" ? "text-accent" : "text-text-tertiary hover:text-text-secondary"}
        `}
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z" />
          <circle cx="12" cy="10" r="3" />
        </svg>
        Mappa
      </button>
    </div>
  );
}
