import { useEffect, useRef, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { AnimatePresence, motion } from "motion/react";
import { X } from "lucide-react";
import { useTranslation } from "react-i18next";

/**
 * A side sheet for the detail of one record. It slides in from the edge it belongs to, closes on
 * Escape or a click outside, keeps focus inside while open and returns it to where it came from.
 */
export function Drawer({ open, title, subtitle, onClose, children, testId }: {
  open: boolean; title: ReactNode; subtitle?: ReactNode; onClose: () => void; children: ReactNode; testId?: string;
}) {
  const { t } = useTranslation();
  const panel = useRef<HTMLDivElement>(null);
  const returnTo = useRef<HTMLElement | null>(null);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;
  useEffect(() => {
    if (!open) return;
    returnTo.current = document.activeElement as HTMLElement | null;
    const timer = window.setTimeout(() => panel.current?.querySelector<HTMLElement>("[data-autofocus]")?.focus(), 30);
    const keys = (e: KeyboardEvent) => {
      if (e.key === "Escape") { e.preventDefault(); closeRef.current(); return; }
      if (e.key !== "Tab" || !panel.current) return;
      const focusable = Array.from(panel.current.querySelectorAll<HTMLElement>('a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'));
      if (!focusable.length) return;
      const first = focusable[0], last = focusable[focusable.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    };
    document.addEventListener("keydown", keys);
    return () => {
      window.clearTimeout(timer);
      document.removeEventListener("keydown", keys);
      returnTo.current?.focus?.();
    };
  }, [open]);
  return createPortal(
    <AnimatePresence>
      {open && (
        <div className="drawer-layer" key="drawer">
          <motion.div className="drawer-scrim" onClick={onClose} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0, transition: { duration: 0.16 } }} transition={{ duration: 0.2 }} />
          <motion.div
            ref={panel}
            className="drawer"
            role="dialog"
            aria-modal="true"
            aria-labelledby="drawer-title"
            data-testid={testId}
            initial={{ x: 48, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 48, opacity: 0, transition: { duration: 0.18, ease: [0.4, 0, 1, 1] } }}
            transition={{ type: "spring", bounce: 0, visualDuration: 0.3 }}
          >
            <div className="drawer-head">
              <div>
                <h2 id="drawer-title">{title}</h2>
                {subtitle && <p className="muted small">{subtitle}</p>}
              </div>
              <button type="button" className="icon-action" onClick={onClose} aria-label={t("common.close")} data-autofocus>
                <X className="nav-icon" aria-hidden="true" />
              </button>
            </div>
            <div className="drawer-body">{children}</div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>,
    document.body,
  );
}
