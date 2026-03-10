import { useCallback, useEffect, useRef } from "react";
import { DrawerHeader } from "./DrawerHeader";

interface AppDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  children: React.ReactNode;
}

/**
 * Chat overlay panel.
 *
 * - Desktop (>=768px): centered modal with rounded corners, backdrop blur
 * - Mobile (<768px): fullscreen, slides up from bottom
 * - Stays mounted (not unmounted) to preserve chat state
 * - Closes on Escape key or backdrop click
 */
export function AppDrawer({ isOpen, onClose, children }: AppDrawerProps) {
  const panelRef = useRef<HTMLDivElement>(null);

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

  // Lock body scroll when open
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
          bg-black/50 backdrop-blur-sm
          transition-opacity duration-300
          ${isOpen ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"}
        `}
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Panel — mobile: fullscreen / desktop: centered modal */}
      <div
        ref={panelRef}
        className="fixed z-50 flex flex-col bg-bg-primary overflow-hidden chat-overlay-panel"
        data-open={isOpen || undefined}
        role="dialog"
        aria-modal="true"
        aria-label="VendoCasa — Chat"
      >
        <DrawerHeader onClose={onClose} />

        {/* Chat content */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {children}
        </div>
      </div>

      {/* Responsive positioning + animation via CSS */}
      <style>{`
        .chat-overlay-panel {
          /* Mobile: fullscreen */
          inset: 0;
          transition: transform 400ms cubic-bezier(0.32, 0.72, 0, 1),
                      opacity 300ms ease;
        }

        /* Mobile closed: slide down */
        .chat-overlay-panel:not([data-open]) {
          transform: translateY(100%);
          opacity: 0;
          pointer-events: none;
        }

        /* Mobile open */
        .chat-overlay-panel[data-open] {
          transform: translateY(0);
          opacity: 1;
          pointer-events: auto;
        }

        /* Desktop: centered modal */
        @media (min-width: 768px) {
          .chat-overlay-panel {
            inset: auto;
            top: 50%;
            left: 50%;
            width: 460px;
            height: 82vh;
            max-height: 720px;
            border-radius: 1rem;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
            border: 1px solid var(--color-border, #2E2E4A);
            transition: transform 400ms cubic-bezier(0.32, 0.72, 0, 1),
                        opacity 300ms ease;
          }

          /* Desktop closed: scale down + fade */
          .chat-overlay-panel:not([data-open]) {
            transform: translate(-50%, -50%) translateY(24px) scale(0.97);
            opacity: 0;
            pointer-events: none;
          }

          /* Desktop open: centered */
          .chat-overlay-panel[data-open] {
            transform: translate(-50%, -50%) translateY(0) scale(1);
            opacity: 1;
            pointer-events: auto;
          }
        }
      `}</style>
    </>
  );
}
