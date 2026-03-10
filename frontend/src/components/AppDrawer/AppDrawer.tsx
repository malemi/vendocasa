import { useCallback, useEffect, useRef } from "react";
import { DrawerHeader } from "./DrawerHeader";

interface AppDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  children: React.ReactNode;
}

/**
 * Full-screen overlay drawer for the chat+map experience.
 *
 * - Desktop (>=768px): slides in from the right
 * - Mobile (<768px): slides up from the bottom
 * - Stays mounted (not unmounted) to preserve chat state
 * - Closes on Escape key
 */
export function AppDrawer({ isOpen, onClose, children }: AppDrawerProps) {
  const drawerRef = useRef<HTMLDivElement>(null);

  // Close on Escape
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    },
    [isOpen, onClose]
  );

  useEffect(() => {
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  // Lock body scroll when drawer is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [isOpen]);

  return (
    <>
      {/* Backdrop */}
      <div
        className={`
          fixed inset-0 z-40
          bg-black/60 backdrop-blur-sm
          transition-opacity duration-300
          ${isOpen ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"}
        `}
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Drawer panel */}
      <div
        ref={drawerRef}
        className="fixed inset-0 z-50 flex flex-col bg-bg-primary"
        style={{
          transition: "transform 400ms cubic-bezier(0.32, 0.72, 0, 1)",
          transform: isOpen ? "translate(0, 0)" : undefined,
        }}
        data-open={isOpen || undefined}
        role="dialog"
        aria-modal="true"
        aria-label="VendoCasa - Valutazione immobiliare"
      >
        <DrawerHeader onClose={onClose} />

        {/* App content area (layout managed by parent) */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {children}
        </div>
      </div>

      {/*
        CSS for the drawer closed state.
        Mobile: slides down (translateY), Desktop: slides right (translateX).
        When data-open is present, both are reset to 0.
      */}
      <style>{`
        .fixed[data-open] {
          /* handled by inline style above */
        }
        .fixed:not([data-open])[role="dialog"] {
          transform: translateY(100%);
        }
        @media (min-width: 768px) {
          .fixed:not([data-open])[role="dialog"] {
            transform: translateX(100%);
          }
        }
      `}</style>
    </>
  );
}
