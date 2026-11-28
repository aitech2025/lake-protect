/* eslint-disable @typescript-eslint/no-explicit-any */
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api, fmtDate, fmtDateTime } from "../api";
import { isAdmin, useAuth } from "../auth";
import { AreaFilter, NO_AREA, inArea, useAreaParams, type Placed } from "../components/AreaFilter";
import { BoundarySeal, useAsync, usePageTitle } from "../components/Bits";
import { MapView } from "../components/MapView";
import { PageState, TableRegion } from "../components/PageState";
import { AddLocation, pick, type Categories } from "./AddLocation";
import { Documents, WeeklyRecord } from "./AssetRecord";
import { CoverageLine, ScreeningSummary } from "./Screening";

/** What GeoGuard watches now and what is planned (app/categories.yaml, D-061). */
function KindsStrip({ cats, kind, setKind }: { cats: Categories; kind: string; setKind: (k: string) => void }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language;
  return (
    <section className="kinds-strip" aria-label={t("locations.what")} data-testid="kinds">
      <button type="button" className="kind-card" aria-pressed={kind === "all"} onClick={() => setKind("all")}>
        <b>{t("locations.all")}</b>
        <span className="small muted">{t("locations.watched_n", { n: cats.items.reduce((a, c) => a + c.watched, 0) })}</span>
      </button>
      {cats.items.map((c) =>
        c.status !== "planned" ? (
          <button key={c.name} type="button" className="kind-card" aria-pressed={kind === c.name} onClick={() => setKind(c.name)} data-testid={`kind-card-${c.name}`}>
            <b>{pick(c.label, lang)}</b>
            <span className="small muted">{c.status === "intake" ? t("locations.from_reports") : t("locations.watched_n", { n: c.watched })}</span>
          </button>
        ) : (
          <details key={c.name} className="kind-card planned" data-testid={`kind-card-${c.name}`}>
            <summary>
              <b>{pick(c.label, lang)}</b> <span className="pill closed">{t("locations.planned")}</span>
            </summary>
            <p className="small">{t("locations.custodians", { who: c.custodians })}</p>
            <p className="small">{t("locations.boundary_from", { what: c.boundary_from })}</p>
            <p className="small"><b>{t("locations.needs")}</b></p>
            <ul className="small">{c.needs.map((n) => <li key={n}>{n}</li>)}</ul>
          </details>
        ),
      )}
    </section>
  );
}

/** Whether the weekly screen watches this location, who changed it and why; the admin stops or resumes it. */
function WatchControl({ assetId, p, onChanged }: { assetId: number; p: any; onChanged: () => void }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language;
  const { user } = useAuth();
  const hist = useAsync(() => api<{ items: any[] }>(`/assets/${assetId}/monitoring`), [assetId, p.monitored]);
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [openIncidents, setOpenIncidents] = useState<number | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  useEffect(() => {
    setOpen(false);
    setReason("");
    setMessage(null);
  }, [assetId]);
  useEffect(() => {
    if (!open || !p.monitored) return;
    api<{ items: any[] }>(`/alerts?asset_id=${assetId}`)
      .then((r) => setOpenIncidents(r.items.filter((i) => ["OPEN", "UNDER_REVIEW"].includes(i.state)).length))
      .catch(() => setOpenIncidents(null));
  }, [open, assetId, p.monitored]);

  const go = async () => {
    setMessage(null);
    try {
      await api(`/assets/${assetId}/monitoring`, { json: { monitored: !p.monitored, reason } });
      setOpen(false);
      setReason("");
      onChanged();
    } catch (e) {
      setMessage((e as Error).message);
    }
  };

  return (
    <section className="section panel" data-testid="watch-control">
      <div className="person-head">
        <h2 className="title-s">{t("locations.watch")}</h2>
        {isAdmin(user) && !open && (
          <button type="button" className={p.monitored ? "btn danger" : "btn"} onClick={() => setOpen(true)} data-testid="watch-toggle">
            {p.monitored ? t("locations.stop") : t("locations.resume")}
          </button>
        )}
      </div>
      <p data-testid="watch-status">
        {p.monitored ? t("locations.watched_since") : <b className="flag">{t("locations.stopped_since", { date: fmtDate(p.monitoring_changed_at, lang), reason: p.monitoring_reason })}</b>}
        {p.added_by && <span className="small muted"> {t("locations.added_by", { name: p.added_by, date: fmtDate(p.added_at, lang) })}</span>}
      </p>
      {open && (
        <div className="watch-form">
          <p className="banner warn">{p.monitored ? t("locations.stop_warn", { n: openIncidents ?? "…" }) : t("locations.resume_warn")}</p>
          <label className="field">{t("locations.reason")}
            <textarea rows={2} value={reason} onChange={(e) => setReason(e.target.value)} data-testid="watch-reason" />
          </label>
          <div className="person-foot">
            <button type="button" className={p.monitored ? "btn danger" : "btn"} disabled={reason.trim().length < 5} onClick={() => void go()} data-testid="watch-confirm">
              {p.monitored ? t("locations.stop") : t("locations.resume")}
            </button>
            <button type="button" className="btn secondary" onClick={() => setOpen(false)}>{t("locations.cancel")}</button>
          </div>
        </div>
      )}
      {message && <p className="banner stop" role="alert">{message}</p>}
      {!!hist.data?.items.length && (
        <>
          <h3 className="small" style={{ marginTop: "0.75rem" }}>{t("locations.history")}</h3>
          <ul className="contract small" data-testid="watch-history">
            {hist.data.items.map((h) => (
              <li key={h.id}><b>{h.monitored ? t("locations.started") : t("locations.stopped")}</b>: {h.actor ?? t("role.system")}, {fmtDateTime(h.at, lang)}. {h.reason}</li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}

export function Assets() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language;
  const { user } = useAuth();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const linked = params.get("asset");
  const [selected, setSelected] = useState<number | null>(linked ? Number(linked) : null);
  useEffect(() => {
    setSelected(linked ? Number(linked) : null);
  }, [linked]);
  const { data, error, status, loading, reload } = useAsync(() => api<{ features: any[] }>("/assets"), []);
  const cats = useAsync(() => api<Categories>("/categories"), []);
  const [kind, setKind] = useState("all");
  const [tab, setTab] = useState<"all" | "lakes" | "lands" | "citizen">("all");
  const reports = useAsync(() => api<{ items: any[] }>("/reports"), []);
  // District, mandal and village, in the address (D-069).
  const [area, setArea] = useAreaParams();
  const [showStopped, setShowStopped] = useState(false);
  const [adding, setAdding] = useState(false);
  const [added, setAdded] = useState<string | null>(null);
  const all = useMemo(() => data?.features ?? [], [data]);
  const places: Placed[] = useMemo(() => (tab === "citizen" ? reports.data?.items ?? [] : all.map((f) => f.properties)), [all, reports.data, tab]);
  const stopped = all.filter((f) => !f.properties.monitored).length;
  const areaKey = `${area.district}|${area.mandal}|${area.village}`;
  const features = useMemo(
    // Places made from citizens' reports are not watched until an official adds them (D-063, D-064),
    // so choosing their kind shows them all.
    () => all.filter((f) => (tab === "all" || (tab === "lakes" ? f.properties.category === "water_body" : tab === "lands" ? f.properties.category !== "water_body" && f.properties.category !== "citizen_reported" : false))
      && (kind === "all" || f.properties.category === kind)
      && inArea(f.properties, area)
      && (showStopped || f.properties.monitored || f.id === selected || kind === "citizen_reported")
      && (!linked || f.id === selected)),
    // `area` is rebuilt on each render; its key says when it changed.
    [all, kind, areaKey, showStopped, selected, linked, tab],
  );
  const labelOf = (category: string) => {
    const c = cats.data?.items.find((x) => x.name === category);
    return c ? pick(c.one, lang) : category;
  };
  usePageTitle(t("assets.title"));
  const { data: versions } = useAsync(() => (selected ? api<{ features: any[] }>(`/assets/${selected}/boundaries`) : Promise.resolve(null)), [selected]);
  const { data: register } = useAsync(() => (selected ? api<any>(`/assets/${selected}/register`) : Promise.resolve(null)), [selected]);

  const mapFc = useMemo(
    () => ({
      type: "FeatureCollection" as const,
      features: features.filter((f) => f.geometry).map((f) => ({ ...f, properties: { kind: f.properties.boundary_kind, status: f.properties.boundary_status } })),
    }),
    [features],
  );
  const selectedFc = useMemo(
    () => (versions ? { type: "FeatureCollection" as const, features: versions.features.filter((f) => f.properties.in_force) } : mapFc),
    [versions, mapFc],
  );
  const reportRows = (reports.data?.items ?? []).filter((r) => tab === "citizen" && inArea(r, area));
  const reportPins = reportRows.filter((r) => r.lon != null && r.lat != null).map((r) => ({ id: r.id, lon: r.lon, lat: r.lat, colour: "#bb5949", label: r.ref, onClick: () => navigate(`/reports/${r.id}`) }));

  const startAdding = () => {
    setSelected(null);
    setAdded(null);
    setAdding(true);
  };

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>{t("assets.title")}</h1>
          <p className="muted" aria-hidden={!data} data-testid="locations-count">{data ? t("locations.count", { n: all.length - stopped }) : " "}</p>
        </div>
        {isAdmin(user) && !adding && <button type="button" className="btn" onClick={startAdding} data-testid="add-location-open">{t("locations.add")}</button>}
      </div>
      {linked && selected && <p><button className="btn quiet" onClick={() => { setSelected(null); setParams({}); }}>{t("locations.back_all")}</button></p>}
      {added && <p className="banner info" role="status" data-testid="added-message">{t("locations.added", { name: added })}</p>}
      {adding && cats.data && (
        <AddLocation
          cats={cats.data}
          context={mapFc}
          places={all.map((f) => f.properties)}
          onCancel={() => setAdding(false)}
          onOpen={(id) => { setAdding(false); setShowStopped(true); setSelected(id); }}
          onAdded={(id, name) => {
            setAdding(false);
            setAdded(name);
            setKind("all");
            setSelected(id);
            reload();
            cats.reload();
          }}
        />
      )}
      {cats.data && tab !== "citizen" && <KindsStrip cats={cats.data} kind={kind} setKind={(k) => { setKind(k); setTab(k === "all" ? "all" : k === "water_body" ? "lakes" : "lands"); }} />}
      <div className="chips asset-tabs" aria-label={t("assets.tabs")} role="group">
        {(["all", "lakes", "lands", "citizen"] as const).map((k) => <button key={k} type="button" className="chip" aria-pressed={tab === k} onClick={() => { setTab(k); setKind("all"); setSelected(null); }}>{t(k === "all" ? "group.all" : `assets.tab.${k}`)}</button>)}
      </div>
      <section className="asset-registry-filters" data-testid="registry-filters" aria-label={t("assets.registry_filters")}>
        <AreaFilter places={places} value={area} onChange={setArea} />
        {(area.district || area.mandal || area.village) && (
          <button type="button" className="btn quiet" onClick={() => setArea(NO_AREA)} data-testid="clear-area-filters">
            {t("assets.clear_area_filters")}
          </button>
        )}
      </section>
      {stopped > 0 && (
        <label className="small toggle-line">
          <input type="checkbox" checked={showStopped} onChange={(e) => setShowStopped(e.target.checked)} data-testid="show-stopped" /> {t("locations.show_stopped", { n: stopped })}
        </label>
      )}
      <p className="note" style={{ marginBottom: 16 }}>{t("assets.real_note")}</p>
      {tab !== "citizen" && <ScreeningSummary />}
      <PageState loading={loading && !data} error={error} status={status} onRetry={reload} />
      <div className="queue asset-queue">
        <div className="mapbox asset-map">
          <MapView boundaries={tab === "citizen" ? undefined : selected ? selectedFc : mapFc} pins={tab === "citizen" ? reportPins : []} />
        </div>
        <div className="list asset-list">
          {tab === "citizen" ? reportRows.map((r) => <button key={r.id} type="button" className="row" onClick={() => navigate(`/reports/${r.id}`)}><span className="bar" style={{ background: "#bb5949" }} /><span><h3>{r.ref} · {t(`reports.what.${r.what}`)}</h3><span className="meta"><span>{r.district ?? t("dashboard.not_recorded")}{r.mandal ? ` · ${r.mandal}` : ""}{r.village ? ` · ${r.village}` : ""}</span><span>{t(`reports.status.${r.status}`)}</span></span></span></button>) : features.map((f) => {
            const p = f.properties;
            return (
              <button key={f.id} className={`row${selected === f.id ? " selected" : ""}`} aria-current={selected === f.id || undefined} onClick={() => navigate(`/assets/${f.id}`)}>
                <span className="bar" style={{ background: !p.monitored ? "#9aa5a0" : p.category === "water_body" ? "#1f6fa8" : "#b08a3e" }} />
                <span>
                  <h3>{lang === "te" && p.name_te ? p.name_te : p.name} {!p.monitored && <span className="pill closed">{t("locations.not_watched")}</span>}</h3>
                  <span className="meta">
                    <span>{labelOf(p.category)}</span>
                    <span>{t(`cohort.${p.cohort}`)}</span>
                    <span>{t(`mode.${p.mode}`)}</span>
                    {p.area_acres !== null && <span>{t("assets.acres", { acres: p.area_acres })}</span>}
                    <span>{t("assets.baseline", { date: fmtDate(p.baseline_date, lang) })}</span>
                    <span>{p.district ?? t("dashboard.not_recorded")}{p.mandal ? " · " + p.mandal : ""}{p.village ? " · " + p.village : ""}</span>
                  </span>
                  {p.boundary_source && <span className="small muted" data-testid="boundary-provenance">{t("assets.boundary_source")}: {p.boundary_source}</span>}
                  <CoverageLine p={p} />
                </span>
                <span><BoundarySeal status={p.boundary_status} version={p.boundary_version} /></span>
              </button>
            );
          })}
        </div>
      </div>
      {versions && (
        <section className="section">
          <h2>{t("assets.versions")}</h2>
          <TableRegion label={t("assets.versions")}>
            <table className="grid" data-testid="boundary-versions">
              <thead>
                <tr><th>#</th><th>{t("detail.boundary")}</th><th>{t("assets.source")}</th><th /></tr>
              </thead>
              <tbody>
                {versions.features.filter((f) => ["ftl", "parcel"].includes(f.properties.kind)).map((f) => {
                  const p = f.properties;
                  return (
                    <tr key={p.id}>
                      <td>{p.version}</td>
                      <td><BoundarySeal status={p.status} /></td>
                      <td>
                        {p.source_url ? <a href={p.source_url} target="_blank" rel="noreferrer">{p.source_name}</a> : p.source_name}
                        {p.notification_ref && <div className="small muted">{p.notification_ref}</div>}
                        <div className="small muted">{t("assets.valid", { from: fmtDate(p.valid_from, lang) })}{p.effective_valid_to ? ` ${t("assets.until", { to: fmtDate(p.effective_valid_to, lang) })}` : ""}</div>
                      </td>
                      <td>{p.in_force ? t("assets.in_force") : t("assets.superseded")}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </TableRegion>
        </section>
      )}
      {selected && all.find((f) => f.id === selected) && (
        <WatchControl assetId={selected} p={all.find((f) => f.id === selected)!.properties} onChanged={() => { reload(); cats.reload(); }} />
      )}
      {selected && <WeeklyRecord assetId={selected} />}
      {selected && <Documents assetId={selected} />}
      {register && (
        <section className="section" data-testid="asset-register">
          <h2>{t("assets.register")}</h2>
          {register.boundary_source?.provenance && (
            <div className="note" data-testid="boundary-provenance">
              <b>{t("assets.provenance")}</b>: {t(`assets.provenance_class.${register.boundary_source.provenance.source_class}`)}
              <div className="small muted">{register.boundary_source.provenance.source_name}</div>
              <div className="small muted">
                {register.boundary_source.provenance.source_date && <>{t("assets.provenance_date", { date: fmtDate(register.boundary_source.provenance.source_date, lang) })} · </>}
                {register.boundary_source.provenance.notification_ref && <>{t("assets.provenance_reference", { ref: register.boundary_source.provenance.notification_ref })} · </>}
                {register.boundary_source.provenance.source_agency ?? ""}
              </div>
              <span className={register.boundary_source.provenance.authority_confirmed ? "pill ok" : "pill closed"}>
                {t(register.boundary_source.provenance.authority_confirmed ? "assets.authority_confirmed" : "assets.authority_unconfirmed")}
              </span>
              {!register.boundary_source.provenance.provenance_complete && <p className="small flag">{t("assets.provenance_incomplete")}</p>}
            </div>
          )}
          {register.links.length === 0 ? (
            <p className="muted">{t("assets.no_links")}</p>
          ) : (
            <ul className="contract">
              {register.links.map((l: any) => (
                <li key={`${l.connector}:${l.external_id}`}>
                  <b>{l.agency}</b>: <code>{l.external_id}</code>
                  <div className="small muted">{l.file_name} · {fmtDate(l.source_date, lang)} · SHA-256 {String(l.sha256).slice(0, 12)}…</div>
                </li>
              ))}
            </ul>
          )}
          <h3 style={{ marginTop: "1rem" }}>{t("assets.parcels")}</h3>
          {register.parcels.length === 0 ? (
            <p className="muted">{t("assets.no_parcels")}</p>
          ) : (
            <>
              {register.core_area_sq_m > 0 && <p className="note" style={{ marginBottom: "0.6rem" }}>{t("assets.core_area", { area: Math.round(register.core_area_sq_m).toLocaleString("en-IN") })}</p>}
              <TableRegion label={t("assets.parcels")}>
                <table className="grid" data-testid="asset-parcels">
                  <thead>
                    <tr><th>{t("assets.col.survey")}</th><th>{t("assets.col.village")}</th><th>{t("assets.col.category")}</th><th>{t("assets.col.extent")}</th><th>{t("assets.col.zone")}</th></tr>
                  </thead>
                  <tbody>
                    {register.parcels.map((p: any) => (
                      <tr key={`${p.village}:${p.survey_no}:${p.sub_division}`}>
                        <td>{p.survey_no}{p.sub_division ? `/${p.sub_division}` : ""}{p.bhudhaar && <div className="small muted">{p.bhudhaar}</div>}</td>
                        <td>{p.village}</td>
                        <td>{t(`land.${p.land_category}`)}{p.core && <b> · {t("assets.core")}</b>}</td>
                        <td>{p.extent_acres ?? ""}</td>
                        <td>{t(`assets.where.${p.zone}`)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </TableRegion>
            </>
          )}
        </section>
      )}
    </div>
  );
}
