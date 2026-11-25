/* eslint-disable @typescript-eslint/no-explicit-any */
import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, fmtDate, type AlertRow } from "../api";
import { useAsync, usePageTitle } from "../components/Bits";
import { MapView, type Pin } from "../components/MapView";
import { PageState } from "../components/PageState";
import { useDemoOnScreen } from "../demo";

type Theme = "dark" | "light";
type LayerKey = "boundaries" | "ftl" | "changes" | "pins";

const LAYERS: { key: LayerKey; label: string; colour: string; hint: string }[] = [
  { key: "boundaries", label: "Cadastral / official boundaries", colour: "#06b6d4", hint: "Certified, preliminary and estimated outlines" },
  { key: "ftl", label: "Lake FTL & buffer zones", colour: "#38bdf8", hint: "Notified lake extent and applicable buffers" },
  { key: "changes", label: "AI change detections", colour: "#ef4444", hint: "Screening polygons awaiting officer review" },
  { key: "pins", label: "Incident & alert locations", colour: "#f59e0b", hint: "Open cases and field activity" },
];

function fmtArea(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return "—";
  return value >= 10000 ? `${(value / 10000).toFixed(2)} ha` : `${Math.round(value).toLocaleString("en-IN")} sq. m`;
}

function Stat({ label, value, tone, sub }: { label: string; value: string | number; tone: string; sub: string }) {
  return <div className="geo-stat"><span className={`geo-stat-dot ${tone}`} /><div><small>{label}</small><strong>{value}</strong><em>{sub}</em></div></div>;
}

export function CommandOverview() {
  const [theme, setTheme] = useState<Theme>((document.documentElement.dataset.theme as Theme) || "dark");
  const [layers, setLayers] = useState<Record<LayerKey, boolean>>({ boundaries: true, ftl: true, changes: true, pins: true });
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [selectedAssetId, setSelectedAssetId] = useState<number | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(true);
  const [inspectorOpen, setInspectorOpen] = useState(true);
  const [compare, setCompare] = useState(false);
  const [swipe, setSwipe] = useState(52);
  const [searchParams] = useSearchParams();
  const [query, setQuery] = useState(searchParams.get("q") ?? "");
  useEffect(() => {
    const syncTheme = (event: Event) => setTheme((event as CustomEvent<Theme>).detail);
    window.addEventListener("geoguard:theme", syncTheme);
    return () => window.removeEventListener("geoguard:theme", syncTheme);
  }, []);
  useEffect(() => { setQuery(searchParams.get("q") ?? ""); }, [searchParams.toString()]);

  const [category, setCategory] = useState("all");

  const assetsState = useAsync(() => api<{ features: any[] }>("/assets"), []);
  const alertsState = useAsync(() => api<{ items: AlertRow[]; has_demo: boolean }>("/alerts"), []);
  const assets = assetsState.data?.features ?? [];
  const alerts = alertsState.data?.items ?? [];
  const demoVisible = assets.some((a) => a.properties?.is_demo) || alerts.some((a) => a.is_demo);
  useDemoOnScreen(demoVisible);
  usePageTitle("Geospatial Command");

  const filteredAssets = useMemo(() => assets.filter((a) => {
    const p = a.properties ?? {};
    if (category === "lakes" && !["lake", "waterbody", "tank"].includes(String(p.asset_type ?? p.kind ?? "").toLowerCase())) return false;
    if (category === "government" && !String(p.asset_type ?? p.kind ?? "").toLowerCase().includes("parcel")) return false;
    if (category === "buildings" && !String(p.asset_type ?? p.kind ?? "").toLowerCase().includes("building")) return false;
    if (query.trim()) {
      const q = query.toLowerCase();
      return [p.name, p.name_te, p.asset_code, p.survey_no, p.id].some((v) => String(v ?? "").toLowerCase().includes(q));
    }
    return true;
  }), [assets, category, query]);

  const filteredAlerts = useMemo(() => alerts.filter((a) => {
    if (category === "lakes" && !["lake", "tank", "waterbody"].includes(a.asset_type.toLowerCase())) return false;
    if (category === "government" && !a.asset_type.toLowerCase().includes("parcel")) return false;
    if (category === "buildings" && !a.asset_type.toLowerCase().includes("building")) return false;
    if (!query.trim()) return true;
    const q = query.toLowerCase();
    return [a.asset_name, a.code, a.asset_id, a.change_type, a.zone].some((v) => String(v ?? "").toLowerCase().includes(q));
  }).sort((a,b) => Number(b.overdue) - Number(a.overdue) || (b.priority_score ?? -1) - (a.priority_score ?? -1)), [alerts, category, query]);

  const selectedAlert = filteredAlerts.find((a) => a.id === selectedId) ?? alerts.find((a) => a.id === selectedId) ?? null;
  useEffect(() => {
    if (selectedId == null && filteredAlerts.length > 0) {
      setSelectedId(filteredAlerts[0].id);
      setSelectedAssetId(filteredAlerts[0].asset_id);
    }
  }, [filteredAlerts, selectedId]);
  const selectedAsset = assets.find((a) => Number(a.properties?.id ?? a.id) === (selectedAlert?.asset_id ?? selectedAssetId)) ?? null;

  const boundaries = useMemo(() => ({
    type: "FeatureCollection" as const,
    features: filteredAssets.filter((f) => f.geometry).map((f) => ({
      ...f,
      properties: {
        ...f.properties,
        kind: f.properties.boundary_kind ?? f.properties.kind ?? "parcel",
        status: f.properties.boundary_status ?? f.properties.status,
      },
    })),
  }), [filteredAssets]);

  const changes = useMemo(() => ({
    type: "FeatureCollection" as const,
    features: filteredAlerts.filter((a) => a.geometry && a.geometry.type !== "Point").map((a) => ({
      type: "Feature" as const, id: a.id, geometry: a.geometry,
      properties: { alert_id: a.id, change_type: a.change_type, status: a.state },
    })),
  }), [filteredAlerts]);

  const pins: Pin[] = useMemo(() => filteredAlerts.map((a) => ({
    id: a.id, lon: a.lon, lat: a.lat,
    colour: a.overdue ? "#ef4444" : ["ACTION", "VERIFY"].includes(a.mode) ? "#f59e0b" : "#06b6d4",
    label: a.asset_name, big: selectedId === a.id,
    onClick: () => selectAlert(a),
  })), [filteredAlerts, selectedId]);

  const selectAlert = (a: AlertRow) => { setSelectedId(a.id); setSelectedAssetId(a.asset_id); setInspectorOpen(true); };
  const selectAssetOnMap = (id: number) => {
    const linked = alerts.find((a) => a.asset_id === id);
    setSelectedAssetId(id);
    setSelectedId(linked?.id ?? null);
    setInspectorOpen(true);
  };
  const toggleLayer = (key: LayerKey) => setLayers((old) => ({ ...old, [key]: !old[key] }));
  const activeCount = alerts.filter((a) => !a.state.startsWith("CLOSED")).length;
  const criticalCount = alerts.filter((a) => a.overdue || (a.priority_score ?? 0) >= 80).length;
  const warningCount = alerts.filter((a) => !a.overdue && (a.priority_score ?? 0) >= 45 && (a.priority_score ?? 0) < 80).length;
  const safeCount = Math.max(0, assets.length - new Set(alerts.map((a) => a.asset_id)).size);
  const focusFit: [number, number, number, number] | null = selectedAlert
    ? [selectedAlert.lon - 0.012, selectedAlert.lat - 0.009, selectedAlert.lon + 0.012, selectedAlert.lat + 0.009] : null;

  return (
    <div className={`geo-command theme-${theme}`}>
      <div className="geo-command-context"><div><small>COMMAND OVERVIEW</small><h1>Geospatial operations</h1></div><div className="geo-context-date"><span>OBSERVATION WINDOW</span><b>Latest available imagery</b></div></div>


      <div className="geo-workspace">
        <aside className={`geo-left-panel ${drawerOpen ? "" : "collapsed"}`}>
          <div className="geo-panel-heading"><div><small>WORKSPACE</small><h2>Map layers</h2></div><button className="geo-icon-btn" onClick={() => setDrawerOpen(!drawerOpen)} aria-label="Collapse layer panel">{drawerOpen ? "‹" : "›"}</button></div>
          {drawerOpen && <>
            <div className="geo-section-label">OPERATIONAL LAYERS <span>4</span></div>
            <div className="geo-layer-list">
              {LAYERS.map((l) => <label className="geo-layer" key={l.key}>
                <span className="geo-layer-swatch" style={{ background: l.colour }} />
                <span className="geo-layer-copy"><b>{l.label}</b><small>{l.hint}</small></span>
                <input type="checkbox" checked={layers[l.key]} onChange={() => toggleLayer(l.key)} />
              </label>)}
            </div>
            <div className="geo-section-label">IMAGERY SOURCE</div>
            <div className="geo-imagery-mode"><button className="active">OPTICAL</button><button disabled title="SAR processing not connected">SAR <i>SOON</i></button><button disabled title="Hybrid basemap not connected">HYBRID</button></div>
            <div className="geo-section-label">THREAT OVERVIEW <span>LIVE DATA</span></div>
            <div className="geo-stat-grid">
              <Stat label="Critical breaches" value={criticalCount} tone="red" sub="Overdue / high priority" />
              <Stat label="Buffer warnings" value={warningCount} tone="amber" sub="Requires assessment" />
              <Stat label="Assets protected" value={safeCount} tone="green" sub="No open linked alert" />
            </div>
            <div className="geo-section-label geo-alert-title">PRIORITY INTELLIGENCE <span>{filteredAlerts.length} OPEN</span></div>
            <div className="geo-alert-feed">
              {filteredAlerts.slice(0, 12).map((a) => <button key={a.id} className={`geo-alert-item ${selectedId === a.id ? "selected" : ""}`} onClick={() => selectAlert(a)}>
                <span className={`geo-alert-indicator ${a.overdue ? "red" : (a.priority_score ?? 0) >= 70 ? "amber" : "cyan"}`} />
                <span className="geo-alert-copy"><b>{a.asset_name}</b><small>{a.change_type.replaceAll("_", " ")} · {a.code}</small><em>{a.overdue ? "OVERDUE ACTION" : `Priority ${Math.round(a.priority_score ?? 0)}`} · {fmtDate(a.first_changed_at, "en")}</em></span>
                <span className="geo-chevron">›</span>
              </button>)}
              {filteredAlerts.length === 0 && <p className="geo-empty">No matching open alerts in this view.</p>}
            </div>
            <div className="geo-feed-footer"><span>Operational records</span><Link to="/alerts">Open alert register ↗</Link></div>
          </>}
        </aside>

        <main className="geo-map-stage">
          <div className="geo-map-toolbar">
            <div className="geo-category-pills">
              {[["all","All assets"],["lakes","Lakes & water"],["government","Government land"],["buildings","Public buildings"]].map(([k,v]) => <button key={k} className={category === k ? "active" : ""} onClick={() => setCategory(k)}>{v}</button>)}
            </div>
            <div className="geo-map-meta"><span>MAP VIEW</span><b>Latest available observations</b><i /> <span>WGS 84</span></div>
          </div>
          <div className="geo-map-canvas">
            {compare ? <>
              <div className="geo-compare-map geo-compare-baseline">
                <MapView boundaries={layers.boundaries || layers.ftl ? boundaries : undefined}
                  fit={focusFit} theme={theme} interactive={false}
                  layerVisibility={{ boundaries: layers.boundaries, ftl: layers.ftl, changes: false }} />
              </div>
              <div className="geo-compare-map geo-compare-latest" style={{ clipPath: `inset(0 0 0 ${swipe}%)` }}>
                <MapView boundaries={layers.boundaries || layers.ftl ? boundaries : undefined}
                  changes={layers.changes ? changes : undefined} pins={layers.pins ? pins : []}
                  fit={focusFit} theme={theme} interactive={false}
                  layerVisibility={{ boundaries: layers.boundaries, ftl: layers.ftl, changes: layers.changes }} />
              </div>
            </> : <MapView boundaries={layers.boundaries || layers.ftl ? boundaries : undefined}
              changes={layers.changes ? changes : undefined} pins={layers.pins ? pins : []}
              fit={focusFit} theme={theme} onAssetClick={selectAssetOnMap}
              layerVisibility={{ boundaries: layers.boundaries, ftl: layers.ftl, changes: layers.changes }} />}
            <div className="geo-map-stamp"><b>HYDERABAD REGION</b><span>Illustrative operational view · source dates vary by asset</span></div>
            <div className="geo-map-legend">
              <span><i className="legend-boundary" /> Official boundary</span><span><i className="legend-ftl" /> FTL / buffer</span><span><i className="legend-change" /> AI screening signal</span><span><i className="legend-pin" /> Open incident</span>
            </div>
            {compare && <div className="geo-compare-divider" style={{ left: `${swipe}%` }}><span>↔</span></div>}
            <div className="geo-map-controls">
              <button title="Zoom in" onClick={() => window.dispatchEvent(new CustomEvent("geoguard:zoom", { detail: 1 }))}>＋</button>
              <button title="Zoom out" onClick={() => window.dispatchEvent(new CustomEvent("geoguard:zoom", { detail: -1 }))}>－</button>
              <button title="Toggle before and after comparison" className={compare ? "active" : ""} onClick={() => setCompare(!compare)}>⇆</button>
              <button title="Reset view" onClick={() => { setSelectedId(null); setSelectedAssetId(null); setInspectorOpen(false); }}>⌖</button>
            </div>
            {compare && <div className="geo-compare-control"><div><b>BASELINE</b><span>Boundary reference</span></div><input aria-label="Before and after comparison divider" type="range" min="5" max="95" value={swipe} onChange={(e) => setSwipe(Number(e.target.value))} /><div><b>LATEST</b><span>Current alert overlay</span></div><p>Swipe preview only. Historical raster pairing is not yet connected.</p></div>}
            <div className="geo-map-bottomline"><span>Coordinates <b>17.4239° N, 78.4738° E</b></span><span>Scale indicative · not for cadastral measurement</span></div>
          </div>
        </main>

        {inspectorOpen && <aside className="geo-inspector">
          <div className="geo-inspector-head"><div><small>ASSET INTELLIGENCE</small><h2>{selectedAlert?.asset_name ?? selectedAsset?.properties?.name ?? "Select a mapped asset"}</h2><span className="geo-asset-id">{selectedAlert?.code ?? selectedAsset?.properties?.asset_code ?? "ASSET RECORD"}</span></div><button className="geo-icon-btn" onClick={() => setInspectorOpen(false)} aria-label="Close inspector">×</button></div>
          {selectedAlert ? <>
            <div className="geo-inspector-tags"><span className="geo-tag red">{selectedAlert.overdue ? "OVERDUE" : selectedAlert.mode}</span><span className="geo-tag neutral">{selectedAlert.state.replaceAll("_"," ")}</span></div>
            <div className="geo-telemetry">
              <div><small>CHANGE AREA</small><b>{fmtArea(selectedAlert.area_sq_m)}</b><span>Reported screening area</span></div>
              <div><small>PRIORITY SCORE</small><b>{selectedAlert.priority_score == null ? "—" : `${Math.round(selectedAlert.priority_score)}/100`}</b><span>Operational triage score</span></div>
              <div><small>CHANGE CLASS</small><b>{selectedAlert.change_type.replaceAll("_"," ")}</b><span>AI / rule screening</span></div>
              <div><small>FIRST OBSERVED</small><b>{fmtDate(selectedAlert.first_changed_at,"en")}</b><span>Recorded event date</span></div>
            </div>
            <section className="geo-inspector-section"><div className="geo-section-label">LOCATION & REFERENCE</div>
              <dl className="geo-facts"><dt>Asset type</dt><dd>{selectedAlert.asset_type.replaceAll("_"," ")}</dd><dt>Zone</dt><dd>{selectedAlert.zone?.replaceAll("_"," ") ?? "Not recorded"}</dd><dt>Sensor basis</dt><dd>{selectedAlert.sensor_basis || "Not recorded"}</dd><dt>Coordinates</dt><dd className="geo-mono">{selectedAlert.lat.toFixed(5)}° N, {selectedAlert.lon.toFixed(5)}° E</dd><dt>Assigned officer</dt><dd>{selectedAlert.owner_name ?? "Unassigned"}</dd></dl>
            </section>
            <section className="geo-inspector-section"><div className="geo-section-label">EVIDENCE STATUS</div><div className="geo-evidence-placeholder"><span>▧</span><div><b>Satellite evidence timeline</b><small>Open the case to inspect available imagery, provenance and field evidence.</small></div></div><p className="geo-disclaimer">A geospatial screening signal is not a legal finding. Boundary status and supporting records must be verified by the competent authority.</p></section>
            <div className="geo-inspector-actions"><Link className="geo-primary-action" to={`/alerts/${selectedAlert.id}`}>Open case file <span>↗</span></Link><Link className="geo-secondary-action" to="/assets">Asset registry</Link></div>
          </> : selectedAsset ? <>
            <div className="geo-inspector-tags"><span className="geo-tag" style={{color:"#6ee7b7",background:"rgba(16,185,129,.14)"}}>ASSET RECORD</span><span className="geo-tag neutral">{String(selectedAsset.properties?.boundary_status ?? "STATUS NOT VERIFIED").replaceAll("_"," ")}</span></div>
            <div className="geo-telemetry">
              <div><small>REGISTERED AREA</small><b>{selectedAsset.properties?.area_acres != null ? Number(selectedAsset.properties.area_acres).toFixed(2) + " acres" : "—"}</b><span>As recorded in asset registry</span></div>
              <div><small>OPEN ALERTS</small><b>{alerts.filter((a) => a.asset_id === Number(selectedAsset.properties?.id ?? selectedAsset.id) && !a.state.startsWith("CLOSED")).length}</b><span>Linked active cases</span></div>
              <div><small>BOUNDARY STATUS</small><b>{String(selectedAsset.properties?.boundary_status ?? "Not recorded").replaceAll("_"," ")}</b><span>Registry status</span></div>
              <div><small>BASELINE REFERENCE</small><b>{fmtDate(selectedAsset.properties?.baseline_date,"en")}</b><span>Reference date, not latest pass</span></div>
            </div>
            <section className="geo-inspector-section"><div className="geo-section-label">ASSET REGISTRY</div>
              <dl className="geo-facts"><dt>Asset category</dt><dd>{String(selectedAsset.properties?.asset_type ?? selectedAsset.properties?.boundary_kind ?? "Public asset").replaceAll("_"," ")}</dd><dt>Asset reference</dt><dd className="geo-mono">{selectedAsset.properties?.asset_code ?? selectedAsset.properties?.id ?? selectedAsset.id}</dd><dt>Governance status</dt><dd>{String(selectedAsset.properties?.boundary_status ?? "Not verified").replaceAll("_"," ")}</dd><dt>Monitoring mode</dt><dd>{String(selectedAsset.properties?.mode ?? "Not recorded")}</dd></dl>
            </section>
            <section className="geo-inspector-section"><p className="geo-disclaimer">Registry details are shown as recorded. Legal boundaries must be checked against the current authenticated notification and survey record.</p></section>
            <div className="geo-inspector-actions"><Link className="geo-primary-action" to="/assets">Open asset registry <span>↗</span></Link><Link className="geo-secondary-action" to="/alerts">View incident register</Link></div>
          </> : <div className="geo-empty-inspector"><span>◎</span><b>No asset selected</b><p>Select a priority alert or mapped asset to inspect its location, change signal and governance record.</p></div>}
        </aside>}
      </div>
      <div className="geo-statusbar"><span><i /> API connected when available</span><span>{filteredAssets.length} assets in view</span><span>{activeCount} active alerts</span><span>DEMO / LIVE status follows selected records</span></div>
      <PageState loading={assetsState.loading && alertsState.loading && !assets.length && !alerts.length}
        error={assetsState.error || alertsState.error} status={assetsState.status || alertsState.status}
        onRetry={() => { assetsState.reload(); alertsState.reload(); }} />
    </div>
  );
}
