import { useEffect, useRef, useState, type MouseEvent } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api } from "../api";
import { useAuth } from "../auth";

// Both roles see every page (D-057); the API remains authoritative for every mutation.
const BOTH = ["admin", "viewer"];
const NAV: { to: string; key: string; roles: string[]; icon: string }[] = [
  { to: "/dashboard", key: "nav.dashboard", roles: BOTH, icon: "dashboard" },
  { to: "/inbox", key: "nav.inbox", roles: BOTH, icon: "inbox" },
  { to: "/alerts", key: "nav.queue", roles: BOTH, icon: "review" },
  { to: "/reports", key: "nav.reports", roles: BOTH, icon: "reports" },
  { to: "/assets", key: "nav.assets", roles: BOTH, icon: "assets" },
  { to: "/records", key: "nav.records", roles: BOTH, icon: "records" },
  { to: "/sources", key: "nav.sources", roles: BOTH, icon: "sources" },
  { to: "/satellites", key: "nav.satellites", roles: BOTH, icon: "satellite" },
  { to: "/monthly", key: "nav.monthly", roles: BOTH, icon: "monthly" },
  { to: "/audit", key: "nav.audit", roles: BOTH, icon: "audit" },
  { to: "/officials", key: "nav.officials", roles: ["admin"], icon: "officials" },
  { to: "/whatsapp-test", key: "nav.whatsapp_test", roles: ["admin"], icon: "channels" },
  { to: "/citizen-operations", key: "nav.citizen_ops", roles: ["admin"], icon: "operations" },
];

const GROUPS = [
  { label: "Workspace", labelTe: "పని ప్రదేశం", items: ["/dashboard", "/inbox"] },
  { label: "Review & records", labelTe: "సమీక్ష & రికార్డులు", items: ["/alerts", "/reports", "/assets", "/records"] },
  { label: "Data & oversight", labelTe: "డేటా & పర్యవేక్షణ", items: ["/sources", "/satellites", "/monthly", "/audit"] },
  { label: "Administration", labelTe: "నిర్వహణ", items: ["/officials", "/whatsapp-test", "/citizen-operations"] },
];

const ICON_PATH: Record<string, string> = {
  dashboard: "M3 3h7v7H3z M14 3h7v4h-7z M14 10h7v11h-7z M3 14h7v7H3z",
  inbox: "M4 4h16v12h-5l-3 4-3-4H4z M8 10h8",
  review: "M4 5h16v14H4z M8 9h8 M8 13h5",
  reports: "M5 3h14v18H5z M8 8h8 M8 12h8 M8 16h5",
  assets: "M3 8 12 3l9 5-9 5z M3 8v9l9 5 9-5V8 M12 13v9",
  records: "M6 3h12v18H6z M9 8h6 M9 12h6 M9 16h6",
  sources: "M4 6h16 M4 12h16 M4 18h16 M7 3v6 M17 9v6",
  satellite: "M5 5 9 9 M15 15l4 4 M14 4l6 6-4 4-6-6z M4 14l6 6 4-4-6-6z",
  monthly: "M4 5h16v16H4z M8 3v4 M16 3v4 M4 10h16 M8 14h3 M8 17h7",
  audit: "M12 3 20 6v5c0 5-3.5 8-8 10-4.5-2-8-5-8-10V6z M8 12l3 3 5-6",
  officials: "M16 20v-1a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v1 M10 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8 M17 11a3 3 0 0 0 0-6 M17 15h1a3 3 0 0 1 3 3v2",
  channels: "M4 5h16v11H8l-4 4z M8 9h8 M8 12h5",
  operations: "M4 4h16v16H4z M8 8h8 M8 12h8 M8 16h4",
};

function NavIcon({ name }: { name: string }) {
  return (
    <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={ICON_PATH[name] ?? ICON_PATH.records} />
    </svg>
  );
}

const COUNT_EVENT = "lp:notify-count";

/** Pages that acknowledge a notification call this, so the navigation count updates at once. */
export function notifyCountChanged(): void {
  window.dispatchEvent(new Event(COUNT_EVENT));
}

function useUnacknowledged(): number {
  const { user } = useAuth();
  const { pathname } = useLocation();
  const [n, setN] = useState(0);
  const [tick, setTick] = useState(0);
  useEffect(() => {
    const bump = () => setTick((x) => x + 1);
    window.addEventListener(COUNT_EVENT, bump);
    const timer = window.setInterval(bump, 60_000);
    return () => {
      window.removeEventListener(COUNT_EVENT, bump);
      window.clearInterval(timer);
    };
  }, []);
  useEffect(() => {
    if (!user) return;
    let live = true;
    api<{ unacknowledged: number }>("/notifications/count")
      .then((r) => live && setN(r.unacknowledged))
      .catch(() => undefined);
    return () => { live = false; };
  }, [user, pathname, tick]);
  return n;
}

function useWhatsAppSimulatorEnabled(): boolean {
  const { user } = useAuth();
  const [enabled, setEnabled] = useState(false);
  useEffect(() => {
    if (!user || user.role !== "admin") {
      setEnabled(false);
      return;
    }
    let live = true;
    api<{ whatsapp_simulator: boolean }>("/citizen/config")
      .then((r) => live && setEnabled(r.whatsapp_simulator))
      .catch(() => live && setEnabled(false));
    return () => { live = false; };
  }, [user]);
  return enabled;
}

export function Mark() {
  // The solid inner outline and dashed outer ring carry the boundary-certainty language.
  return (
    <svg width="38" height="30" viewBox="0 0 40 28" aria-hidden="true">
      <path d="M6 15c0-6 6-10 13-10s15 3 15 9-6 10-14 10S6 21 6 15z" fill="#0f4c5c" stroke="#ffffff" strokeWidth="2" />
      <path d="M2 15c0-8 8-13 17-13s19 4 19 12-8 13-18 13S2 23 2 15z" fill="none" stroke="#8a5300" strokeWidth="1.5" strokeDasharray="3 2.5" />
    </svg>
  );
}

export function Layout() {
  const { t, i18n } = useTranslation();
  const { user, logout } = useAuth();
  const { pathname } = useLocation();
  const unacknowledged = useUnacknowledged();
  const simulatorEnabled = useWhatsAppSimulatorEnabled();
  const mainRef = useRef<HTMLElement>(null);
  const firstRender = useRef(true);
  const toggle = () => void i18n.changeLanguage(i18n.language === "te" ? "en" : "te");
  const visible = NAV.filter((n) => user && n.roles.includes(user.role) && (n.to !== "/whatsapp-test" || simulatorEnabled));
  const active = NAV.filter((n) => pathname === n.to || pathname.startsWith(n.to + "/")).sort((a, b) => b.to.length - a.to.length)[0];

  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false;
      return;
    }
    const main = mainRef.current;
    if (!main) return;
    main.scrollTop = 0;
    main.focus({ preventScroll: true });
  }, [pathname]);

  const skipToContent = (e: MouseEvent<HTMLAnchorElement>) => {
    e.preventDefault();
    mainRef.current?.focus();
  };

  return (
    <div className="shell civic-shell">
      <a className="skip-link" href="#main" onClick={skipToContent}>{t("nav.skip")}</a>
      <aside className="rail civic-rail">
        <NavLink to="/dashboard" className="brand" aria-label={t("app.name")}>
          <Mark />
          <span className="brand-copy">
            <b>{t("app.name")}</b>
            <span className="small">{t("app.tagline")}</span>
          </span>
        </NavLink>
        <div className="rail-caption">{i18n.language === "te" ? "పరిపాలనా కార్యస్థలం" : "GOVERNANCE WORKSPACE"}</div>
        <nav className="nav-links" aria-label={t("nav.label")}>
          {GROUPS.map((group) => {
            const items = visible.filter((n) => group.items.includes(n.to));
            if (!items.length) return null;
            return (
              <section className="nav-group" key={group.label} aria-label={i18n.language === "te" ? group.labelTe : group.label}>
                <p className="nav-group-label">{i18n.language === "te" ? group.labelTe : group.label}</p>
                {items.map((n) => (
                  <NavLink key={n.to} to={n.to} data-testid={`nav-${n.to.slice(1)}`} className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}>
                    <NavIcon name={n.icon} />
                    <span>{t(n.key)}</span>
                    {n.to === "/inbox" && unacknowledged > 0 && (
                      <span className="nav-count" data-testid="inbox-count" aria-label={t("inbox.count_label", { count: unacknowledged })}>{unacknowledged}</span>
                    )}
                  </NavLink>
                ))}
              </section>
            );
          })}
        </nav>
        <div className="rail-foot">
          <span className="rail-foot-mark" aria-hidden="true">●</span>
          <span>Evidence-led public administration</span>
        </div>
      </aside>
      <header className="topbar">
        <div className="topbar-context">
          <span className="topbar-kicker">GEOGUARD <span aria-hidden="true">/</span> TELANGANA</span>
          <p className="topbar-page-title">{active ? t(active.key) : t("app.name")}</p>
        </div>
        <div className="topbar-tools">
          <span className="role-indicator"><span className="role-dot" />{user && t(`role.${user.role}`)}</span>
          <span className="topbar-divider" aria-hidden="true" />
          <span className="user-name">{user?.name}</span>
          <button className="utility-button language-button" onClick={toggle} lang={i18n.language === "te" ? "en" : "te"}>{i18n.language === "te" ? "English" : "తెలుగు"}</button>
          <button className="utility-button logout-button" onClick={logout}>{t("nav.logout")}</button>
        </div>
      </header>
      <main className="main civic-main" id="main" ref={mainRef} tabIndex={-1}>
        <Outlet />
      </main>
    </div>
  );
}
