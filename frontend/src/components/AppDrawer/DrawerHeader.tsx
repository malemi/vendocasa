import { Logo } from "../ui/Logo";

interface DrawerHeaderProps {
  onClose: () => void;
}

export function DrawerHeader({ onClose }: DrawerHeaderProps) {
  return (
    <header className="flex items-center justify-between px-4 py-3 bg-bg-elevated border-b border-border shrink-0">
      <Logo size="sm" />

      <button
        onClick={onClose}
        className="
          w-9 h-9 flex items-center justify-center
          rounded-lg text-text-secondary
          hover:text-text-primary hover:bg-bg-surface
          transition-colors duration-150 cursor-pointer
        "
        title="Chiudi"
        aria-label="Chiudi applicazione"
      >
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinecap="round"
        >
          <path d="M18 6L6 18M6 6l12 12" />
        </svg>
      </button>
    </header>
  );
}
