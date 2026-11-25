import { useCallback, useEffect, useRef } from "react";
import { DrawerHeader } from "./DrawerHeader";

interface AppDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  /** Present when a user is signed in. */
  onSignOut?: () => void;
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
const FOCUSABLE =
  'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

export function AppDrawer({ isOpen, onClose, onSignOut, children }: AppDrawerProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLElement | null>(null);

  // Hidden: inert, so neither the keyboard nor assistive technology reaches it.
  // Opened: focus moves inside; closed: focus returns to what opened it.
  useEffect(() => {
    const panel = panelRef.current;
    if (!panel) return;
    panel.toggleAttribute("inert", !isOpen);
    if (isOpen) {
      triggerRef.current = document.activeElement as HTMLElement | null;
      const first = panel.querySelector<HTMLElement>(FOCUSABLE);
      (first ?? panel).focus();
    } else if (triggerRef.current) {
      triggerRef.current.focus();
      triggerRef.current = null;
    }
  }, [isOpen]);

  // Escape closes; Tab and Shift+Tab stay inside the open panel.
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (!isOpen) return;
      if (e.key === "Escape") {
        onClose();
        return;
      }
      if (e.key !== "Tab" || !panelRef.current) return;
      const focusable = Array.from(panelRef.current.querySelectorAll<HTMLElement>(FOCUSABLE));
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      const active = document.activeElement;
      if (e.shiftKey && (active === first || !panelRef.current.contains(active))) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && (active === last || !panelRef.current.contains(active))) {
        e.preventDefault();
        first.focus();
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
        aria-hidden={isOpen ? undefined : true}
        tabIndex={-1}
      >
        <DrawerHeader onClose={onClose} onSignOut={onSignOut} />

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
