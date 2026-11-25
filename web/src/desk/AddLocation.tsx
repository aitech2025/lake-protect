/* eslint-disable @typescript-eslint/no-explicit-any */
import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../api";
import { useAsync } from "../components/Bits";
import { MapView } from "../components/MapView";

export type Category = {
  name: string;
  status: "live" | "planned" | "intake";
  label: { en: string; te: string };
  one: { en: string; te: string };
  primary_kind: "ftl" | "parcel";
  custodians: string;
  boundary_from: string;
  watch_for: string[];
  needs: string[];
  types: { type: string; label: { en: string; te: string } }[];
  watched: number;
};
export type Categories = { items: Category[]; limits: { min_area_sq_m: number; max_area_sq_km: number }; policy_cutoff_date: string };

type Poly = GeoJSON.Polygon | GeoJSON.MultiPolygon;
type Check = { ok: boolean; area_sq_m?: number; area_acres?: number; reason?: string; asset_id?: number | null };

// Boundary statuses a location of each kind may have (api/app/services/locations.py).
const STATUSES = {
  ftl: ["physically_marked", "final_notification", "preliminary_notification", "derived"],
  parcel: ["physically_marked", "surveyed_agency", "survey_number_only", "derived"],
} as const;
const CONFIRMED = ["physically_marked", "final_notification", "surveyed_agency"];
const DRAWN_SOURCE = "Drawn by the admin on the Sentinel-2 base map";

export const pick = (l: { en: string; te: string }, lang: string) => (lang === "te" ? l.te : l.en);

/** Polygons from a GeoJSON file: a geometry, a Feature or a FeatureCollection. */
function fromGeoJson(text: string): Poly {
  const data = JSON.parse(text);
  const geoms: any[] =
    data.type === "FeatureCollection" ? data.features.map((f: any) => f.geometry) : data.type === "Feature" ? [data.geometry] : [data];
  const polys: number[][][][] = [];
  for (const g of geoms) {
    if (g?.type === "Polygon") polys.push(g.coordinates);
    else if (g?.type === "MultiPolygon") polys.push(...g.coordinates);
  }
  if (!polys.length) throw new Error("no Polygon or MultiPolygon in it");
  return polys.length === 1 ? { type: "Polygon", coordinates: polys[0] } : { type: "MultiPolygon", coordinates: polys };
}

/** Polygons from a KML file (Google Earth): each Polygon's outer and inner rings. */
function fromKml(text: string): Poly {
  const doc = new DOMParser().parseFromString(text, "application/xml");
  if (doc.getElementsByTagName("parsererror").length) throw new Error("not valid KML");
  const ring = (el: Element | null) =>
    (el?.getElementsByTagName("coordinates")[0]?.textContent ?? "")
      .trim()
      .split(/\s+/)
      .filter(Boolean)
      .map((c) => c.split(",").slice(0, 2).map(Number));
  const polys = Array.from(doc.getElementsByTagName("Polygon")).map((p) => [
    ring(p.getElementsByTagName("outerBoundaryIs")[0] ?? null),
    ...Array.from(p.getElementsByTagName("innerBoundaryIs")).map((i) => ring(i)),
  ]);
  if (!polys.length || polys.some((p) => p[0].length < 4)) throw new Error("no Polygon with at least three corners in it");
  return polys.length === 1 ? { type: "Polygon", coordinates: polys[0] } : { type: "MultiPolygon", coordinates: polys };
}

/** Admin only (DECISIONS.md D-061): a new location with its outline, watched from the next weekly screen. */
export function AddLocation({ cats, context, onAdded, onCancel, onOpen }: {
  cats: Categories;
  context: GeoJSON.FeatureCollection;
  onAdded: (id: number, name: string) => void;
  onCancel: () => void;
  onOpen: (id: number) => void;
}) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language;
  const live = cats.items.filter((c) => c.status === "live");
  const [category, setCategory] = useState(live[0]?.name ?? "");
  const cat = cats.items.find((c) => c.name === category);
  const [type, setType] = useState(cat?.types[0]?.type ?? "");
  const [f, setF] = useState({ name: "", name_te: "", district: "", mandal: "", village: "", survey: "", custodian: "", notes: "",
    baseline: cats.policy_cutoff_date, source_name: DRAWN_SOURCE, source_date: "", source_url: "", notification_ref: "", status: "derived" });
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => setF((x) => ({ ...x, [k]: e.target.value }));
  const [mode, setMode] = useState<"draw" | "upload">("draw");
  const [points, setPoints] = useState<[number, number][]>([]);
  const [closed, setClosed] = useState(false);
  const [uploaded, setUploaded] = useState<Poly | null>(null);
  const [fileNote, setFileNote] = useState<string | null>(null);
  const [check, setCheck] = useState<Check | null>(null);
  const [error, setError] = useState<{ text: string; assetId?: number } | null>(null);
  const [busy, setBusy] = useState(false);
  const areas = useAsync(() => api<{ items: { district: string; mandals: { mandal: string }[] }[] }>("/areas"), []);
  const districts = areas.data?.items ?? [];
  const mandals = districts.find((d) => d.district.toLowerCase() === f.district.trim().toLowerCase())?.mandals ?? [];

  useEffect(() => {
    if (cat && !cat.types.some((x) => x.type === type)) setType(cat.types[0]?.type ?? "");
    if (cat && !(STATUSES[cat.primary_kind] as readonly string[]).includes(f.status)) setF((x) => ({ ...x, status: "derived" }));
  }, [cat, type, f.status]);
  useEffect(() => {
    setF((x) => ({ ...x, status: mode === "draw" ? "derived" : x.status, source_name: mode === "draw" ? DRAWN_SOURCE : x.source_name === DRAWN_SOURCE ? "" : x.source_name }));
  }, [mode]);

  const geometry: Poly | null = useMemo(() => {
    if (mode === "upload") return uploaded;
    return closed && points.length >= 3 ? { type: "Polygon", coordinates: [[...points, points[0]]] } : null;
  }, [mode, uploaded, closed, points]);

  useEffect(() => {
    setCheck(null);
    if (!geometry) return;
    let stop = false;
    const id = window.setTimeout(() => {
      api<Check>("/assets/outline-check", { json: { geometry } }).then((c) => !stop && setCheck(c)).catch((e) => !stop && setCheck({ ok: false, reason: String(e.message) }));
    }, 250);
    return () => {
      stop = true;
      window.clearTimeout(id);
    };
  }, [geometry]);

  const readFile = async (file: File | undefined) => {
    setUploaded(null);
    setFileNote(null);
    if (!file) return;
    try {
      const text = await file.text();
      const poly = /\.kml$/i.test(file.name) || text.trimStart().startsWith("<") ? fromKml(text) : fromGeoJson(text);
      setUploaded(poly);
      setF((x) => ({ ...x, source_name: x.source_name || file.name }));
    } catch (e) {
      setFileNote(t("locations.file_bad", { why: (e as Error).message }));
    }
  };

  const preview = useMemo(() => {
    const features = [...context.features];
    if (mode === "upload" && uploaded) features.push({ type: "Feature", properties: { kind: "parcel", status: "derived" }, geometry: uploaded });
    return { type: "FeatureCollection" as const, features };
  }, [context, mode, uploaded]);

  const kind = cat?.primary_kind ?? "parcel";
  const needsRef = CONFIRMED.includes(f.status);
  const ready = !!(cat && type && f.name.trim() && f.district.trim() && f.source_name.trim() && geometry && check?.ok && (!needsRef || f.notification_ref.trim()));

  const submit = async () => {
    if (!ready || !geometry) return;
    setBusy(true);
    setError(null);
    try {
      const out = await api<any>("/assets", {
        json: {
          type, name: f.name, name_te: f.name_te || null, district: f.district, mandal: f.mandal || null, village: f.village || null,
          survey_numbers: f.survey.split(",").map((s) => s.trim()).filter(Boolean), custodian_agency: f.custodian || null,
          baseline_date: f.baseline || null, notes: f.notes || null, geometry, drawn: mode === "draw", status: f.status,
          source_name: f.source_name, source_url: f.source_url || null, source_date: f.source_date || null,
          notification_ref: f.notification_ref || null,
        },
      });
      onAdded(out.id, out.properties.name);
    } catch (e) {
      const msg = (e as Error).message;
      try {
        const d = JSON.parse(msg);
        setError({ text: d.message, assetId: d.asset_id });
      } catch {
        setError({ text: msg });
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="panel add-location" aria-labelledby="add-title" data-testid="add-location">
      <div className="page-head" style={{ marginBottom: "0.5rem" }}>
        <div>
          <h2 id="add-title">{t("locations.add_title")}</h2>
          <p className="small muted">{t("locations.add_lede")}</p>
        </div>
        <button type="button" className="btn secondary" onClick={onCancel}>{t("locations.cancel")}</button>
      </div>

      <fieldset className="kinds">
        <legend>{t("locations.kind")}</legend>
        {cats.items.filter((c) => c.status !== "intake").map((c) => (
          <label key={c.name} className={`kind ${c.status}`} data-testid={`kind-${c.name}`}>
            <input type="radio" name="category" value={c.name} checked={category === c.name} disabled={c.status !== "live"} onChange={() => setCategory(c.name)} />
            <span>
              <b>{pick(c.label, lang)}</b>
              <span className="small muted">{c.status === "live" ? t("locations.watched_n", { n: c.watched }) : t("locations.planned")}</span>
            </span>
          </label>
        ))}
      </fieldset>

      <div className="add-grid">
        <div className="add-fields">
          <label className="field">{t("locations.type")}
            <select value={type} onChange={(e) => setType(e.target.value)} data-testid="loc-type">
              {cat?.types.map((x) => <option key={x.type} value={x.type}>{pick(x.label, lang)}</option>)}
            </select>
          </label>
          <label className="field">{t("locations.name")}<input value={f.name} onChange={set("name")} required data-testid="loc-name" /></label>
          <label className="field">{t("locations.name_te")}<input value={f.name_te} onChange={set("name_te")} lang="te" /></label>
          <label className="field">{t("locations.district")}
            <input value={f.district} onChange={set("district")} list="loc-districts" required data-testid="loc-district" />
            <datalist id="loc-districts">{districts.map((d) => <option key={d.district} value={d.district} />)}</datalist>
          </label>
          <label className="field">{t("locations.mandal")}
            <input value={f.mandal} onChange={set("mandal")} list="loc-mandals" data-testid="loc-mandal" />
            <datalist id="loc-mandals">{mandals.map((m) => <option key={m.mandal} value={m.mandal} />)}</datalist>
          </label>
          <label className="field">{t("locations.village")}<input value={f.village} onChange={set("village")} /></label>
          <label className="field">{t("locations.survey_numbers")}<input value={f.survey} onChange={set("survey")} placeholder="123, 124/A" /></label>
          <label className="field">{t("locations.custodian")}<input value={f.custodian} onChange={set("custodian")} placeholder={cat?.custodians} /></label>
          <label className="field">{t("locations.baseline")}
            <input type="date" value={f.baseline} onChange={set("baseline")} max={new Date().toISOString().slice(0, 10)} />
            <span className="small muted">{t("locations.baseline_help")}</span>
          </label>
        </div>

        <div className="add-outline">
          <div className="chips" role="group" aria-label={t("locations.outline")}>
            <button type="button" className="chip" aria-pressed={mode === "draw"} onClick={() => setMode("draw")} data-testid="mode-draw">{t("locations.draw")}</button>
            <button type="button" className="chip" aria-pressed={mode === "upload"} onClick={() => setMode("upload")} data-testid="mode-upload">{t("locations.upload")}</button>
          </div>
          {mode === "draw" ? (
            <>
              <p className="small muted">{t("locations.draw_help")}</p>
              <div className="mapbox" style={{ height: 340 }}>
                <MapView boundaries={context} draft={points} draftClosed={closed}
                  onMapClick={closed ? undefined : (p) => setPoints((ps) => [...ps, p])} testId="draw-map" />
              </div>
              <div className="draw-tools">
                <span className="small" data-testid="draw-points">{t("locations.points", { n: points.length })}</span>
                <button type="button" className="btn secondary" disabled={!points.length} onClick={() => { setClosed(false); setPoints((ps) => ps.slice(0, -1)); }}>{t("locations.undo")}</button>
                <button type="button" className="btn secondary" disabled={!points.length} onClick={() => { setClosed(false); setPoints([]); }}>{t("locations.clear")}</button>
                <button type="button" className="btn" disabled={points.length < 3 || closed} onClick={() => setClosed(true)} data-testid="draw-finish">{t("locations.finish")}</button>
              </div>
            </>
          ) : (
            <>
              <label className="field">{t("locations.upload_help")}
                <input type="file" accept=".geojson,.json,.kml,application/geo+json,application/vnd.google-earth.kml+xml" onChange={(e) => void readFile(e.target.files?.[0])} data-testid="loc-file" />
              </label>
              {fileNote && <p className="banner warn" role="alert">{fileNote}</p>}
              <div className="mapbox" style={{ height: 300 }}>
                <MapView boundaries={preview} />
              </div>
            </>
          )}
          <p className="small" role="status" data-testid="outline-check">
            {geometry && !check && t("locations.checking")}
            {check?.ok && <b>{t("locations.area", { sqm: Math.round(check.area_sq_m ?? 0).toLocaleString("en-IN"), acres: check.area_acres })}</b>}
            {check && !check.ok && <span className="flag">{check.reason}</span>}
            {check && !check.ok && check.asset_id && <> <button type="button" className="btn quiet" onClick={() => onOpen(check.asset_id!)}>{t("locations.same_place")}</button></>}
          </p>

          <label className="field">{t("locations.source_name")}<input value={f.source_name} onChange={set("source_name")} required data-testid="loc-source" /></label>
          <label className="field">{t("locations.status")}
            {mode === "draw" ? (
              <span className="note" data-testid="loc-status-drawn">{t("locations.status_drawn")}</span>
            ) : (
              <select value={f.status} onChange={set("status")} data-testid="loc-status">
                {STATUSES[kind].map((s) => <option key={s} value={s}>{t(`boundary.${s}`)}</option>)}
              </select>
            )}
          </label>
          {mode === "upload" && (
            <>
              <label className="field">{t("locations.notification_ref")}
                <input value={f.notification_ref} onChange={set("notification_ref")} required={needsRef} data-testid="loc-ref" />
                {needsRef && <span className="small muted">{t("locations.notification_ref_help")}</span>}
              </label>
              <label className="field">{t("locations.source_date")}<input type="date" value={f.source_date} onChange={set("source_date")} max={new Date().toISOString().slice(0, 10)} /></label>
              <label className="field">{t("locations.source_url")}<input type="url" value={f.source_url} onChange={set("source_url")} /></label>
            </>
          )}
          <label className="field">{t("locations.notes")}<textarea rows={2} value={f.notes} onChange={set("notes")} /></label>
        </div>
      </div>

      {error && (
        <p className="banner stop" role="alert" data-testid="add-error">
          {error.text} {error.assetId && <button type="button" className="btn quiet" onClick={() => onOpen(error.assetId!)}>{t("locations.same_place")}</button>}
        </p>
      )}
      <div className="person-foot">
        <button type="button" className="btn" disabled={!ready || busy} onClick={() => void submit()} data-testid="loc-submit">{t("locations.submit")}</button>
      </div>
    </section>
  );
}
