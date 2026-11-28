import { useEffect, useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";
import { ArrowRight, Footprints, Landmark, Languages, Lock, MapPinned, Megaphone, ShieldCheck } from "lucide-react";
import { api, API_BASE, fmtDate, type User } from "../api";
import { homeFor, useAuth } from "../auth";
import { PageState } from "../components/PageState";
import { LineSwatch, usePageTitle } from "../components/Bits";
import { BrandMark } from "../components/Brand";

// Central Hyderabad at zoom 12: the lakes the weekly screen watches, from the offline Sentinel-2 base map.
const TILE_Z = 12;
const TILE_X = [2938, 2939, 2940, 2941, 2942];
const TILE_Y = [1845, 1846, 1847, 1848];

const ROLE_ICON: Record<string, ReactNode> = {
  admin: <ShieldCheck />,
  senior_official: <Landmark />,
  district_officer: <MapPinned />,
  field_officer: <Footprints />,
};

type Meta = { bounds?: number[]; scenes?: { acquired_at: string }[]; attribution?: string };

/** The satellite base map, drawn from local tiles. Shown only when the base map has been built. */
function Imagery() {
  const { t, i18n } = useTranslation();
  const [meta, setMeta] = useState<Meta | null>(null);
  const [loaded, setLoaded] = useState(0);
  useEffect(() => {
    let live = true;
    fetch(`${API_BASE}/tiles/s2/meta.json`)
      .then((r) => (r.ok ? r.json() : null))
      .then((m: Meta | null) => live && setMeta(m?.bounds ? m : null))
      .catch(() => undefined);
    return () => { live = false; };
  }, []);
  if (!meta) return null;
  const latest = (meta.scenes ?? []).map((s) => s.acquired_at).sort().pop();
  return (
    <>
      <div className={`login-imagery${loaded >= 8 ? " ready" : ""}`} style={{ ["--cols" as string]: TILE_X.length, ["--scale" as string]: 1.2 }} aria-hidden="true">
        {TILE_Y.flatMap((y) => TILE_X.map((x) => (
          <img key={`${x}-${y}`} src={`${API_BASE}/tiles/s2/${TILE_Z}/${x}/${y}.jpg`} alt="" onLoad={() => setLoaded((n) => n + 1)} />
        )))}
      </div>
      <p className="login-caption">
        {t("login.imagery_caption", { date: latest ? fmtDate(latest, i18n.language) : "" })} · {meta.attribution}
      </p>
    </>
  );
}

export function Login() {
  const { t, i18n } = useTranslation();
  const { login } = useAuth();
  const nav = useNavigate();
  const [users, setUsers] = useState<User[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  usePageTitle(t("login.title"));

  useEffect(() => {
    let live = true;
    api<User[]>("/auth/demo-users").then((value) => live && setUsers(value)).catch((e: Error) => live && setError(e.message)).finally(() => live && setLoading(false));
    return () => { live = false; };
  }, []);

  const go = async (username: string) => {
    setBusy(username);
    setError(null);
    try {
      const u = await login(username);
      nav(homeFor(u.role));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  };

  return (
    <main className="login-screen">
      <aside className="login-aside">
        <div className="login-brand">
          <BrandMark />
          <span><b>{t("app.name")}</b><small>{t("app.region")}</small></span>
        </div>
        <div>
          <div className="login-aside-copy">
            <h1>{t("app.tagline")}</h1>
            <p>{t("login.platform")}</p>
            <div className="login-legend" aria-label={t("boundary.legend_title")}>
              <span><LineSwatch colour="#ffffff" />{t("boundary.legend_solid")}</span>
              <span><LineSwatch colour="#ffffff" dash="6 4" />{t("boundary.legend_dashed")}</span>
              <span><LineSwatch colour="#ffffff" dash="1.5 3" />{t("boundary.legend_dotted")}</span>
            </div>
          </div>
          <Imagery />
        </div>
      </aside>
      <section className="login-panel" aria-labelledby="login-heading">
        <div className="login-panel-head">
          <Link to="/report" className="login-public-link"><Megaphone aria-hidden="true" />{t("login.citizen")}</Link>
          <button className="utility-button" onClick={() => void i18n.changeLanguage(i18n.language === "te" ? "en" : "te")} lang={i18n.language === "te" ? "en" : "te"}>
            <Languages size={15} aria-hidden="true" />{t("nav.language")}
          </button>
        </div>
        <div className="login-form-content">
          <h2 id="login-heading">{t("login.title")}</h2>
          <p className="muted">{t("login.intro")}</p>
          {error && <p className="banner stop" role="alert">{t("error.load", { msg: error })}</p>}
          <PageState loading={loading} />
          <div className="roles" role="group" aria-label={t("login.title")}>
            {users.map((u) => (
              <button key={u.id} type="button" data-role={u.role} disabled={busy !== null} onClick={() => void go(u.username)} data-testid={`login-${u.username}`}>
                <span className="role-avatar" aria-hidden="true">{ROLE_ICON[u.role] ?? <Landmark />}</span>
                <span className="role-name">{t(`role.${u.role}`)}<small>{u.name}</small></span>
                <ArrowRight className="role-go" size={18} aria-hidden="true" />
                <span className="role-desc">{busy === u.username ? t("login.signing_in") : t(`login.role.${u.role}`)}</span>
              </button>
            ))}
          </div>
          <p className="login-security"><Lock aria-hidden="true" />{t("login.secure_note")}</p>
        </div>
        <footer className="login-panel-foot"><span>{t("app.name")}, {t("login.footer")}</span><span>{t("app.region")}</span></footer>
      </section>
    </main>
  );
}
