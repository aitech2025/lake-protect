import { useEffect, useRef, useState, type MouseEvent, type FormEvent } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../auth";
import { DemoBand } from "../demo";

const NAV: { to: string; label: string; glyph: string; roles: string[] }[] = [
  { to: "/command", label: "Command overview", glyph: "⌖", roles: ["analyst","reviewer","nodal_officer","legal_officer","senior_officer","admin","auditor"] },
  { to: "/alerts", label: "Incident register", glyph: "◉", roles: ["analyst","reviewer","nodal_officer","legal_officer","senior_officer","admin","auditor"] },
  { to: "/assets", label: "Asset registry", glyph: "▱", roles: ["admin","nodal_officer","analyst","legal_officer"] },
  { to: "/records", label: "Legal records", glyph: "▤", roles: ["admin","legal_officer","nodal_officer","analyst"] },
  { to: "/monthly", label: "Reports & analytics", glyph: "▥", roles: ["senior_officer","nodal_officer","legal_officer","admin","auditor"] },
  { to: "/audit", label: "Audit trail", glyph: "◷", roles: ["auditor","admin"] },
];

export function Mark() {
  return <svg width="34" height="34" viewBox="0 0 40 40" aria-hidden="true">
    <path d="M20 2 36 11v18L20 38 4 29V11z" fill="none" stroke="currentColor" strokeWidth="1.5"/>
    <path d="M8 23c5-9 9 6 16-2s7-1 8-5M9 28c5-5 10 4 21-3" fill="none" stroke="#38bdf8" strokeWidth="2.2" strokeLinecap="round"/>
  </svg>;
}

export function Layout() {
  const { t, i18n } = useTranslation();
  const { user, logout } = useAuth();
  const { pathname } = useLocation();
  const nav = useNavigate();
  const mainRef = useRef<HTMLElement>(null);
  const firstRender = useRef(true);
  const [theme, setTheme] = useState<"dark"|"light">(() => {
    try { return localStorage.getItem("lp.theme") === "light" ? "light" : "dark"; }
    catch { return "dark"; }
  });
  const [search, setSearch] = useState("");
  const toggle = () => void i18n.changeLanguage(i18n.language === "te" ? "en" : "te");
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    window.dispatchEvent(new CustomEvent("geoguard:theme", { detail: theme }));
    try { localStorage.setItem("lp.theme", theme); } catch { /* optional preference */ }
  }, [theme]);
  useEffect(() => {
    if (firstRender.current) { firstRender.current = false; return; }
    const main = mainRef.current;
    if (!main) return;
    main.scrollTop = 0;
    main.focus({ preventScroll: true });
  }, [pathname]);
  const skipToContent = (e: MouseEvent<HTMLAnchorElement>) => { e.preventDefault(); mainRef.current?.focus(); };
  const submitSearch = (e: FormEvent) => { e.preventDefault(); nav(search.trim() ? `/command?q=${encodeURIComponent(search.trim())}` : "/command"); };

  return (
    <div className="shell geo-shell">
      <a className="skip-link" href="#main" onClick={skipToContent}>{t("nav.skip")}</a>
      <DemoBand />
      <header className="geo-globalbar">
        <Link to="/command" className="geo-brand-lockup"><span className="geo-brand-mark"><Mark /></span><span><b>GeoGuard</b><small>GEOSPATIAL INTELLIGENCE PLATFORM</small></span></Link>
        <div className="geo-global-jurisdiction"><small>JURISDICTION</small><b>Telangana <span>›</span> Hyderabad <span>›</span> State view</b></div>
        <form className="geo-global-search" onSubmit={submitSearch}><span>⌕</span><input value={search} onChange={(e)=>setSearch(e.target.value)} placeholder="Search survey no., lake, asset or coordinates…" aria-label="Search GeoGuard"/><kbd>⌘ K</kbd></form>
        <div className="geo-global-actions">
          <span className="geo-online-indicator"><i/> OPERATIONAL</span>
          <button className="geo-top-icon" onClick={()=>setTheme(theme==="dark"?"light":"dark")} aria-label="Toggle dark and light theme" title="Toggle theme">{theme==="dark"?"☼":"◐"}</button>
          <button className="geo-top-icon" onClick={toggle} lang={i18n.language==="te"?"en":"te"} title="Change language">{i18n.language==="te"?"EN":"తె"}</button>
          <div className="geo-profile"><span>GO</span><div><b>{user?.name ?? "Officer"}</b><small>{user ? t(`role.${user.role}`) : "GOVERNMENT USER"}</small></div></div>
          <button className="geo-signout" onClick={logout} title="Sign out">↗</button>
        </div>
      </header>
      <nav className="rail geo-rail" aria-label={t("nav.label")}>
        <div className="geo-rail-label">OPERATIONS</div>
        {NAV.filter((n)=>user && n.roles.includes(user.role)).map((n)=>(
          <NavLink key={n.to} to={n.to} className={({isActive})=>isActive?"active":""}>
            <span className="geo-nav-glyph">{n.glyph}</span><span>{n.label}</span>
          </NavLink>
        ))}
        <div className="geo-rail-bottom"><span className="geo-rail-label">PLATFORM STATUS</span><div><i/> Data services connected</div><small>GeoGuard · Pilot environment</small></div>
      </nav>
      <main className="main geo-main" id="main" ref={mainRef} tabIndex={-1}><Outlet /></main>
    </div>
  );
}
