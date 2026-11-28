import { useId, type ReactNode } from "react";
import { motion } from "motion/react";

export type SegmentOption<T extends string> = { value: T; label: ReactNode; testId?: string; count?: number | null };

/**
 * A row of mutually exclusive choices. The raised thumb slides to the chosen option, so the change
 * of selection is visible. As toggles they are buttons with aria-pressed; as tabs, a tablist.
 */
export function Segmented<T extends string>({
  options, value, onChange, label, mode = "toggle", className = "",
}: {
  options: SegmentOption<T>[];
  value: T;
  onChange: (value: T) => void;
  label: string;
  mode?: "toggle" | "tabs";
  className?: string;
}) {
  const id = useId();
  const tabs = mode === "tabs";
  return (
    <div className={`chips segmented ${className}`} role={tabs ? "tablist" : "group"} aria-label={label}>
      {options.map((o) => {
        const on = o.value === value;
        return (
          <button
            key={o.value}
            type="button"
            className={`chip${on ? " active" : ""}`}
            role={tabs ? "tab" : undefined}
            aria-selected={tabs ? on : undefined}
            aria-pressed={tabs ? undefined : on}
            tabIndex={tabs && !on ? -1 : undefined}
            data-testid={o.testId}
            onClick={() => onChange(o.value)}
            onKeyDown={tabs ? (e) => {
              if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
              e.preventDefault();
              const i = options.findIndex((x) => x.value === value);
              const next = options[(i + (e.key === "ArrowRight" ? 1 : -1) + options.length) % options.length];
              onChange(next.value);
              const row = e.currentTarget.parentElement;
              requestAnimationFrame(() => (row?.querySelector('[aria-selected="true"]') as HTMLElement | null)?.focus());
            } : undefined}
          >
            {on && <motion.span layoutId={`${id}-thumb`} className="chip-thumb" transition={{ type: "spring", bounce: 0, visualDuration: 0.25 }} />}
            <span className="chip-label">{o.label}</span>
            {o.count != null && <span className="chip-label chip-count">{o.count}</span>}
          </button>
        );
      })}
    </div>
  );
}
