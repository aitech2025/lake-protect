import { createContext, useCallback, useContext, useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";

/**
 * Which world the desk shows: the real lakes of Hyderabad (screened from Sentinel-2) or the
 * fictional demo world. They are never mixed on one screen (CONTEXT.md section 13, demo data
 * rules), and the choice is remembered per viewer only, as a convenience.
 */
export type Dataset = "demo" | "real";

const KEY = "lp.dataset";
const Ctx = createContext<{ dataset: Dataset; setDataset: (d: Dataset) => void }>({ dataset: "demo", setDataset: () => {} });

function initial(): Dataset {
  try {
    return localStorage.getItem(KEY) === "real" ? "real" : "demo";
  } catch {
    return "demo";
  }
}

export function DatasetProvider({ children }: { children: ReactNode }) {
  const [dataset, set] = useState<Dataset>(initial);
  const setDataset = useCallback((d: Dataset) => {
    set(d);
    try {
      localStorage.setItem(KEY, d);
    } catch {
      /* still switches for this tab */
    }
  }, []);
  return <Ctx.Provider value={{ dataset, setDataset }}>{children}</Ctx.Provider>;
}

export function useDataset() {
  return useContext(Ctx);
}

/** Base map for a world: the Sentinel-2 mosaic for real lakes, the drawn map for the demo. */
export function baseFor(dataset: Dataset): "s2" | "demo" {
  return dataset === "real" ? "s2" : "demo";
}

export function DatasetSwitch() {
  const { t } = useTranslation();
  const { dataset, setDataset } = useDataset();
  return (
    <div className="dataset-switch" role="group" aria-label={t("dataset.label")}>
      <span className="small">{t("dataset.label")}</span>
      <button className="chip" aria-pressed={dataset === "real"} onClick={() => setDataset("real")} data-testid="dataset-real">
        {t("dataset.real")}
      </button>
      <button className="chip" aria-pressed={dataset === "demo"} onClick={() => setDataset("demo")} data-testid="dataset-demo">
        {t("dataset.demo")}
      </button>
    </div>
  );
}
