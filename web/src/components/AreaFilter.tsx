import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";

/**
 * District, mandal and village pickers (D-069), the same on every page that narrows a list by area.
 *
 * Each list holds only the areas inside the one picked above it, and picking a lower one first
 * fills in the ones above when they are certain. The area lives in the address
 * (?district=&mandal=&village=), so a narrowed list can be refreshed or shared, and the Overview's
 * links open it already narrowed. Names match as the API matches them: case and spaces aside, and
 * "-" means "area not recorded".
 */
export const AREA_LEVELS = ["district", "mandal", "village"] as const;
export type AreaLevel = (typeof AREA_LEVELS)[number];
export type Area = Record<AreaLevel, string>;
export type Placed = Partial<Record<AreaLevel, string | null>>;
export const NO_AREA: Area = { district: "", mandal: "", village: "" };

const NOT_RECORDED = "-";
const norm = (s: string | null | undefined) => (s ?? "").trim();
const key = (s: string | null | undefined) => norm(s).toLowerCase();
/** Does a place's name for a level match a wanted one? */
const matches = (have: string | null | undefined, want: string) => key(have) === (want === NOT_RECORDED ? "" : key(want));

/** Is a place inside the area? Levels left empty match anything. */
export function inArea(p: Placed, area: Area): boolean {
  return AREA_LEVELS.every((k) => !area[k] || matches(p[k], area[k]));
}

/** The area in the address, and a setter that keeps the address's other filters. */
export function useAreaParams(): [Area, (next: Area) => void] {
  const [params, setParams] = useSearchParams();
  const area: Area = { district: params.get("district") ?? "", mandal: params.get("mandal") ?? "", village: params.get("village") ?? "" };
  const set = (next: Area) =>
    setParams((prev) => {
      const q = new URLSearchParams(prev);
      AREA_LEVELS.forEach((k) => (next[k] ? q.set(k, next[k]) : q.delete(k)));
      return q;
    }, { replace: true });
  return [area, set];
}

/** The names at one level among the places inside the levels picked above it, sorted. */
export function areaOptions(places: Placed[], level: AreaLevel, area: Area): string[] {
  const above = AREA_LEVELS.slice(0, AREA_LEVELS.indexOf(level));
  const names = new Map<string, string>();
  for (const p of places) {
    if (!above.every((k) => !area[k] || matches(p[k], area[k]))) continue;
    const name = norm(p[level]);
    if (name && !names.has(name.toLowerCase())) names.set(name.toLowerCase(), name);
  }
  // A name from the address stays shown even when no place on the page carries it.
  if (area[level] && !names.has(key(area[level]))) names.set(key(area[level]), area[level]);
  return [...names.values()].sort((a, b) => a.localeCompare(b, "en"));
}

/** The area after picking `value` at `level`: the levels below are cleared; those above are filled when certain. */
export function pickArea(places: Placed[], level: AreaLevel, value: string, area: Area): Area {
  const at = AREA_LEVELS.indexOf(level);
  const next: Area = { ...area, [level]: value };
  AREA_LEVELS.slice(at + 1).forEach((k) => (next[k] = ""));
  if (!value || value === NOT_RECORDED) return next;
  const holders = places.filter((p) => matches(p[level], value) && AREA_LEVELS.slice(0, at).every((k) => !area[k] || matches(p[k], area[k])));
  for (const k of AREA_LEVELS.slice(0, at)) {
    if (next[k]) continue;
    const above = new Set(holders.map((p) => norm(p[k])).filter(Boolean));
    if (above.size === 1) next[k] = [...above][0];
  }
  return next;
}

type Props = {
  /** The places the list holds: the options come from them. */
  places: Placed[];
  value: Area;
  onChange: (next: Area) => void;
  /** How many levels to offer: district only, district and mandal, or all three. */
  levels?: 1 | 2 | 3;
  /** Test ids are `${testId}-district`, `${testId}-mandal` and `${testId}-village`. */
  testId?: string;
};

export function AreaFilter({ places, value, onChange, levels = 3, testId = "filter" }: Props) {
  const { t } = useTranslation();
  return (
    <>
      {AREA_LEVELS.slice(0, levels).map((level) => {
        const options = areaOptions(places, level, value);
        // The address may spell a name differently from the data; show the data's spelling.
        const current = options.find((o) => key(o) === key(value[level])) ?? value[level];
        return (
          <label className="field" key={level}>
            {t(`assets.filter_${level}`)}
            <select value={current} disabled={options.length === 0} onChange={(e) => onChange(pickArea(places, level, e.target.value, value))} data-testid={`${testId}-${level}`}>
              <option value="">{t(`assets.all_${level}s`)}</option>
              {options.map((o) => <option key={o} value={o}>{o === NOT_RECORDED ? t("dashboard.not_recorded") : o}</option>)}
            </select>
          </label>
        );
      })}
    </>
  );
}
