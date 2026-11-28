/* eslint-disable @typescript-eslint/no-explicit-any */
import { useEffect, useId, useMemo, useRef, useState, type KeyboardEvent as ReactKeyboardEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { AnimatePresence, motion } from "motion/react";
import { ArrowRight, CornerDownLeft, FileText, MapPin, ScanSearch, Search, Navigation } from "lucide-react";
import { api } from "../api";

export type PageCommand = { to: string; label: string; group: string };
type Result = { id: string; to: string; kind: "assets" | "incidents" | "citizen" | "pages"; title: string; detail: string };
type SearchData = { assets: any[]; alerts: any[]; reports: any[] };

const BOUNDARY = /[\s\-_/.:]/;

/** Fuzzy score of a query against a label: characters in order, rewarding word starts and runs. */
function score(text: string, query: string): number {
  const t = text.toLocaleLowerCase();
  let cursor = 0;
  let total = 0;
  let streak = 0;
  for (let i = 0; i < query.length; i++) {
    const at = t.indexOf(query[i], cursor);
    if (at < 0) return -1;
    streak = at === cursor && i > 0 ? streak + 1 : 0;
    total += 2 + streak * 4;
    if (at === 0) total += 12;
    else if (BOUNDARY.test(t[at - 1])) total += 8;
    cursor = at + 1;
  }
  return total - text.length * 0.05;
}

const KIND_ICON = { assets: MapPin, incidents: ScanSearch, citizen: FileText, pages: Navigation };

/**
 * Search across locations, incidents and citizen reports, plus a jump to any page the person can open.
 * A combobox: arrow keys move through results, Enter opens one, Escape closes. Each source loads on
 * its own, so one that fails is named and can be retried without hiding the others.
 */
export function GlobalSearch({ pages }: { pages: PageCommand[] }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const uid = useId();
  const ref = useRef<HTMLInputElement>(null);
  const boxRef = useRef<HTMLDivElement>(null);
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [failedSources, setFailedSources] = useState<string[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [active, setActive] = useState(0);
  const [data, setData] = useState<SearchData>({ assets: [], alerts: [], reports: [] });

  useEffect(() => {
    const shortcut = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        ref.current?.focus();
        ref.current?.select();
      }
    };
    window.addEventListener("keydown", shortcut);
    return () => window.removeEventListener("keydown", shortcut);
  }, []);

  useEffect(() => {
    if (!open) return;
    const away = (e: PointerEvent) => {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", away);
    return () => document.removeEventListener("pointerdown", away);
  }, [open]);

  const load = async (retry = false) => {
    if ((!retry && loaded) || loading) return;
    setLoading(true);
    const [assets, alerts, reports] = await Promise.allSettled([
      api<{ features: any[] }>("/assets"),
      api<{ items: any[] }>("/alerts"),
      api<{ items: any[] }>("/reports"),
    ]);
    setFailedSources([
      ...(assets.status === "rejected" ? ["assets"] : []),
      ...(alerts.status === "rejected" ? ["incidents"] : []),
      ...(reports.status === "rejected" ? ["citizen"] : []),
    ]);
    setData({
      assets: assets.status === "fulfilled" ? assets.value.features ?? [] : [],
      alerts: alerts.status === "fulfilled" ? alerts.value.items ?? [] : [],
      reports: reports.status === "fulfilled" ? reports.value.items ?? [] : [],
    });
    setLoaded(true);
    setLoading(false);
  };

  const term = query.trim().toLocaleLowerCase();
  const results = useMemo<Result[]>(() => {
    const pageHits = pages
      .map((p) => ({ p, s: term ? score(p.label, term) : 0 }))
      .filter((x) => x.s >= 0)
      .sort((a, b) => b.s - a.s)
      .slice(0, term ? 3 : 8)
      .map(({ p }) => ({ id: `page-${p.to}`, to: p.to, kind: "pages" as const, title: p.label, detail: p.group }));
    if (!term) return pageHits;
    const contains = (value: unknown) => String(value ?? "").toLocaleLowerCase().includes(term);
    const assets = data.assets
      .filter((a) => [a.properties?.name, a.properties?.name_te, a.properties?.asset_code, a.properties?.district, a.properties?.mandal, a.properties?.village, a.properties?.asset_key].some(contains))
      .slice(0, 4)
      .map((a) => ({ id: `asset-${a.id}`, to: `/assets/${a.id}`, kind: "assets" as const, title: a.properties?.name, detail: [a.properties?.asset_code, a.properties?.district, a.properties?.mandal].filter(Boolean).join(", ") }));
    const alerts = data.alerts
      .filter((a) => [a.code, a.asset_name, a.summary, a.change_label].some(contains))
      .slice(0, 4)
      .map((a) => ({ id: `alert-${a.id}`, to: `/alerts/${a.id}`, kind: "incidents" as const, title: `${a.asset_name}`, detail: [a.code, a.change_label].filter(Boolean).join(", ") }));
    const reports = data.reports
      .filter((r) => [r.ref, r.location_text, r.description, r.district].some(contains))
      .slice(0, 4)
      .map((r) => ({ id: `report-${r.id}`, to: `/reports/${r.id}`, kind: "citizen" as const, title: r.ref, detail: r.location_text ?? r.district ?? r.description ?? "" }));
    const found: Result[] = [...assets, ...alerts, ...reports].slice(0, 9);
    return found.concat(pageHits);
  }, [data, term, pages]);

  useEffect(() => {
    setActive(0);
  }, [term]);
  const activeId = results[active] ? `${uid}-${results[active].id}` : undefined;

  const close = () => {
    setOpen(false);
    setQuery("");
  };
  const go = (r: Result) => {
    close();
    ref.current?.blur();
    navigate(r.to);
  };
  const onKeyDown = (e: ReactKeyboardEvent<HTMLInputElement>) => {
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      setOpen(true);
      if (!results.length) return;
      const delta = e.key === "ArrowDown" ? 1 : -1;
      const next = (active + delta + results.length) % results.length;
      setActive(next);
      document.getElementById(`${uid}-${results[next].id}`)?.scrollIntoView({ block: "nearest" });
    } else if (e.key === "Enter" && open && results[active]) {
      e.preventDefault();
      go(results[active]);
    } else if (e.key === "Escape") {
      e.preventDefault();
      if (query) setQuery("");
      else {
        setOpen(false);
        ref.current?.blur();
      }
    }
  };

  const showPanel = open && (results.length > 0 || !!term);
  const listed = showPanel && results.length > 0;
  const groups: { kind: Result["kind"]; items: { r: Result; i: number }[] }[] = [];
  results.forEach((r, i) => {
    const last = groups[groups.length - 1];
    if (last && last.kind === r.kind) last.items.push({ r, i });
    else groups.push({ kind: r.kind, items: [{ r, i }] });
  });
  return (
    <div className="global-search" ref={boxRef}>
      <Search className="search-glyph" aria-hidden="true" />
      <input
        ref={ref}
        id="global-search-input"
        type="text"
        role="combobox"
        aria-expanded={listed}
        aria-controls={listed ? "global-search-results" : undefined}
        aria-autocomplete="list"
        aria-activedescendant={listed ? activeId : undefined}
        autoComplete="off"
        spellCheck={false}
        value={query}
        placeholder={t("search.placeholder")}
        aria-label={t("search.label")}
        onFocus={() => { setOpen(true); void load(); }}
        onChange={(e) => { setQuery(e.target.value); setOpen(true); }}
        onKeyDown={onKeyDown}
      />
      <kbd aria-hidden="true">Ctrl K</kbd>
      <AnimatePresence>
        {showPanel && (
          <motion.div
            key="results"
            className="search-results"
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4, transition: { duration: 0.12 } }}
            transition={{ duration: 0.18, ease: [0.22, 1, 0.36, 1] }}
            onMouseDown={(e) => e.preventDefault()}
          >
            {loading && term && <p className="search-state" role="status">{t("search.loading")}</p>}
            {!loading && term && results.every((r) => r.kind === "pages") && failedSources.length === 0 && <p className="search-state" role="status">{t("search.empty")}</p>}
            {listed && (
              <div id="global-search-results" role="listbox" aria-label={t("search.results")}>
                {groups.map((g) => (
                  <div key={g.kind} role="group" aria-labelledby={`${uid}-g-${g.kind}`}>
                    <p className="search-group" id={`${uid}-g-${g.kind}`}>{t(`search.group.${g.kind}`)}</p>
                    {g.items.map(({ r, i }) => {
                      const Icon = KIND_ICON[r.kind];
                      return (
                        <Link
                          key={r.id}
                          to={r.to}
                          id={`${uid}-${r.id}`}
                          role="option"
                          aria-selected={i === active}
                          tabIndex={-1}
                          onPointerMove={() => setActive(i)}
                          onClick={() => { close(); ref.current?.blur(); }}
                        >
                          <span className="result-icon" aria-hidden="true"><Icon /></span>
                          <span><b>{r.title}</b>{r.detail && <em>{r.detail}</em>}</span>
                          <ArrowRight className="result-go" size={16} aria-hidden="true" />
                        </Link>
                      );
                    })}
                  </div>
                ))}
              </div>
            )}
            {failedSources.length > 0 && (
              <div className="search-unavailable" role="status" data-testid="search-partial">
                <span>{failedSources.length === 3 ? t("search.unavailable") : t("search.partial", { sources: failedSources.map((source) => t(`search.group.${source}`)).join(", ") })}</span>
                <button type="button" onClick={() => void load(true)} disabled={loading}>{t("search.retry")}</button>
              </div>
            )}
            {failedSources.length === 0 && (
              <p className="search-hint" aria-hidden="true">
                <span><kbd>↑</kbd><kbd>↓</kbd>{t("search.move")}</span>
                <span><kbd><CornerDownLeft size={11} /></kbd>{t("search.open")}</span>
                <span><kbd>Esc</kbd>{t("search.close")}</span>
              </p>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
