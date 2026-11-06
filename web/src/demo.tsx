import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";

/** Section 9.1: a visible "Demo data" badge whenever is_demo records are on screen. */
const DemoContext = createContext<{ count: number; setCount: (fn: (n: number) => number) => void }>({ count: 0, setCount: () => {} });

export function DemoProvider({ children }: { children: ReactNode }) {
  const [count, setCount] = useState(0);
  return <DemoContext.Provider value={{ count, setCount }}>{children}</DemoContext.Provider>;
}

/** A page calls this with true while it shows demo records. */
export function useDemoOnScreen(onScreen: boolean): void {
  const { setCount } = useContext(DemoContext);
  useEffect(() => {
    if (!onScreen) return;
    setCount((n) => n + 1);
    return () => setCount((n) => n - 1);
  }, [onScreen, setCount]);
}

export function DemoBand() {
  const { count } = useContext(DemoContext);
  const { t } = useTranslation();
  if (count <= 0) return null;
  return (
    <div className="demo-band" role="status" data-testid="demo-badge">
      <strong>{t("demo.badge")}</strong>
      <span>{t("demo.explain")}</span>
    </div>
  );
}

export function DemoTag() {
  const { t } = useTranslation();
  return <span className="demo-tag">{t("demo.badge")}</span>;
}
