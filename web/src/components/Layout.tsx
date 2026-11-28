import { useEffect, useMemo, useRef, useState, type ComponentType, type MouseEvent } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { AnimatePresence, motion } from "motion/react";
import {
  Activity, CalendarRange, ChevronDown, ClipboardList, Database, FolderOpen, Inbox, Landmark, Languages, LayoutGrid, LogOut,
  Map as MapIcon, MapPin, Menu, MessageSquareText, MessagesSquare, Monitor, Moon, PanelLeftClose, PanelLeftOpen, Satellite,
  ScanSearch, ShieldCheck, Sun, Users,
} from "lucide-react";
import { api, fmtDate } from "../api";
import { homeFor, isAdmin, useAuth } from "../auth";
import { applyTheme, savedTheme, type Theme } from "../theme";
import { BrandMark } from "./Brand";
import { GlobalSearch, type PageCommand } from "./GlobalSearch";

type Icon = ComponentType<{ className?: string; "aria-hidden"?: boolean | "true" }>;

// What each persona sees (D-067). The API remains authoritative for every read and every step.
const ALL = ["admin", "senior_official", "district_officer", "field_officer"];
const AREA = ["admin", "senior_official", "district_officer"];
const STATE = ["admin", "senior_official"];
const NAV: { to: string; key: string; roles: string[]; icon: Icon }[] = [
  { to: "/dashboard", key: "nav.dashboard", roles: AREA, icon: LayoutGrid },
  { to: "/map", key: "nav.map", roles: ALL, icon: MapIcon },
  { to: "/inbox", key: "nav.inbox", roles: ALL, icon: Inbox },
  { to: "/alerts", key: "nav.queue", roles: ALL, icon: ScanSearch },
  { to: "/reports", key: "nav.reports", roles: AREA, icon: MessageSquareText },
  { to: "/assets", key: "nav.assets", roles: AREA, icon: MapPin },
  { to: "/registry", key: "nav.registry", roles: STATE, icon: Landmark },
  { to: "/records", key: "nav.records", roles: STATE, icon: FolderOpen },
  { to: "/monthly", key: "nav.monthly", roles: STATE, icon: CalendarRange },
  { to: "/sources", key: "nav.sources", roles: STATE, icon: Database },
  { to: "/satellites", key: "nav.satellites", roles: STATE, icon: Satellite },
  { to: "/audit", key: "nav.audit", roles: STATE, icon: ShieldCheck },
  { to: "/system", key: "nav.system", roles: ["admin"], icon: Activity },
  { to: "/officials", key: "nav.officials", roles: ["admin"], icon: Users },
  { to: "/whatsapp-test", key: "nav.whatsapp_test", roles: ["admin"], icon: MessagesSquare },
  { to: "/citizen-operations", key: "nav.citizen_ops", roles: ["admin"], icon: ClipboardList },
];
const GROUPS = [
  { key: "nav.group.workspace", items: ["/alerts", "/dashboard", "/map", "/inbox"], fieldOnly: true },
  { key: "nav.group.workspace", items: ["/dashboard", "/map", "/inbox"] },
  { key: "nav.group.investigations", items: ["/alerts", "/reports"] },
  { key: "nav.group.registry", items: ["/assets", "/registry", "/records", "/monthly"] },
  { key: "nav.group.data", items: ["/sources", "/satellites", "/audit", "/system"] },
  { key: "nav.group.admin", items: ["/officials", "/whatsapp-test", "/citizen-operations"] },
];

const COUNT_EVENT = "lp:notify-count";
/** Pages that acknowledge a notification call this, so the navigation count updates at once. */
export function notifyCountChanged(): void { window.dispatchEvent(new Event(COUNT_EVENT)); }

function useUnacknowledged(): number {
  const { user } = useAuth();
  const { pathname } = useLocation();
  const [n, setN] = useState(0);
  const [tick, setTick] = useState(0);
  useEffect(() => {
    const bump = () => setTick((x) => x + 1);
    window.addEventListener(COUNT_EVENT, bump);
    const timer = window.setInterval(bump, 60_000);
    return () => { window.removeEventListener(COUNT_EVENT, bump); window.clearInterval(timer); };
  }, []);
  useEffect(() => {
    if (!user) return;
    let live = true;
    api<{ unacknowledged: number }>("/notifications/count").then((r) => live && setN(r.unacknowledged)).catch(() => undefined);
    return () => { live = false; };
  }, [user, pathname, tick]);
  return n;
}

function useWhatsAppSimulatorEnabled(): boolean {
  const { user } = useAuth();
  const [enabled, setEnabled] = useState(false);
  useEffect(() => {
    if (!user || user.role !== "admin") { setEnabled(false); return; }
    let live = true;
    api<{ whatsapp_simulator: boolean }>("/citizen/config").then((r) => live && setEnabled(r.whatsapp_simulator)).catch(() => live && setEnabled(false));
    return () => { live = false; };
  }, [user]);
  return enabled;
}

type Run = { as_of: string; rule_version: string; assets_total: number; coverage: Record<string, number> | null };

/** The latest weekly screen from space, as a status line at the foot of the navigation. */
function ScreenStatus() {
  const { t, i18n } = useTranslation();
  const [run, setRun] = useState<Run | null | undefined>(undefined);
  useEffect(() => {
    let live = true;
    api<{ items: Run[] }>("/screening/runs?limit=1&dataset=real").then((r) => live && setRun(r.items?.[0] ?? null)).catch(() => live && setRun(undefined));
    return () => { live = false; };
  }, []);
  if (run === undefined) return null;
  if (run === null) return <div className="rail-foot" data-testid="rail-screen"><span><i className="pass-dot none" aria-hidden="true" />{t("rail.never")}</span></div>;
  const age = (Date.now() - new Date(run.as_of + "T00:00:00Z").getTime()) / 86_400_000;
  const cov = run.coverage ?? {};
  const seen = (cov.no_candidate ?? 0) + (cov.candidate_found ?? 0);
  return (
    <div className="rail-foot" data-testid="rail-screen">
      <span><i className={`pass-dot${age > 10 ? " stale" : ""}`} aria-hidden="true" /><b>{t("rail.screen", { date: fmtDate(run.as_of, i18n.language) })}</b></span>
      <span>{t("rail.seen", { seen, total: run.assets_total })}</span>
      <span className="mono">{t("rail.rules", { rule: run.rule_version })}</span>
    </div>
  );
}

function ProfileMenu() {
  const { t } = useTranslation();
  const { user, logout } = useAuth();
  const ref = useRef<HTMLDetailsElement>(null);
  const [theme, setTheme] = useState<Theme>(savedTheme);
  useEffect(() => {
    const away = (e: PointerEvent) => {
      if (ref.current?.open && !ref.current.contains(e.target as Node)) ref.current.open = false;
    };
    const esc = (e: KeyboardEvent) => {
      if (e.key === "Escape" && ref.current?.open) {
        ref.current.open = false;
        ref.current.querySelector("summary")?.focus();
      }
    };
    document.addEventListener("pointerdown", away);
    document.addEventListener("keydown", esc);
    return () => { document.removeEventListener("pointerdown", away); document.removeEventListener("keydown", esc); };
  }, []);
  const pick = (value: Theme) => { setTheme(value); applyTheme(value); };
  const themes: { v: Theme; icon: Icon }[] = [{ v: "light", icon: Sun }, { v: "dark", icon: Moon }, { v: "system", icon: Monitor }];
  return (
    <details className="profile-menu" ref={ref}>
      <summary title={t("nav.account", { name: user?.name ?? "" })}>
        <span className="profile-avatar" aria-hidden="true">{user?.name?.trim().slice(0, 1).toLocaleUpperCase() ?? "G"}</span>
        <span className="profile-copy"><b>{user?.name}</b><small>{user && t(`role.${user.role}`)}</small></span>
        <ChevronDown className="profile-chevron" aria-hidden="true" />
      </summary>
      <div className="profile-dropdown">
        <div className="profile-ident"><b>{user?.name}</b><span>{user && t(`role.${user.role}`)}</span></div>
        <p className="menu-label" id="theme-label">{t("theme.label")}</p>
        <div className="menu-segment" role="group" aria-labelledby="theme-label">
          {themes.map(({ v, icon: I }) => (
            <button key={v} type="button" aria-pressed={theme === v} onClick={() => pick(v)} title={t(`theme.${v}`)}>
              <span className="sr-only">{t(`theme.${v}`)}</span><I aria-hidden="true" className="nav-icon" />
            </button>
          ))}
        </div>
        <div className="menu-sep" />
        <button type="button" className="menu-item danger" onClick={logout}><LogOut className="nav-icon" aria-hidden="true" />{t("nav.logout")}</button>
      </div>
    </details>
  );
}

export function Layout() {
  const { t, i18n } = useTranslation();
  const { user } = useAuth();
  const { pathname } = useLocation();
  const unacknowledged = useUnacknowledged();
  const simulatorEnabled = useWhatsAppSimulatorEnabled();
  const mainRef = useRef<HTMLElement>(null);
  const firstRender = useRef(true);
  const [collapsed, setCollapsed] = useState(() => {
    try { return window.localStorage.getItem("lp-nav-collapsed") === "true"; } catch { return false; }
  });
  const [mobileOpen, setMobileOpen] = useState(false);
  const toggleLanguage = () => void i18n.changeLanguage(i18n.language === "te" ? "en" : "te");
  const field = user?.role === "field_officer";
  const label = (n: { to: string; key: string }) => (field && n.to === "/alerts" ? "nav.field_visits" : n.key);
  const groups = GROUPS.filter((g) => !!g.fieldOnly === field);
  const visible = NAV.filter((n) => user && n.roles.includes(user.role) && (n.to !== "/whatsapp-test" || simulatorEnabled));
  const active = NAV.filter((n) => pathname === n.to || pathname.startsWith(n.to + "/")).sort((a, b) => b.to.length - a.to.length)[0];
  const group = groups.find((g) => active && g.items.includes(active.to));
  const pages: PageCommand[] = useMemo(
    () => visible.map((n) => ({ to: n.to, label: t(label(n)), group: t(groups.find((g) => g.items.includes(n.to))?.key ?? "nav.group.workspace") })),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [visible.length, i18n.language, t],
  );

  useEffect(() => {
    try { window.localStorage.setItem("lp-nav-collapsed", String(collapsed)); } catch { /* convenience only */ }
  }, [collapsed]);
  useEffect(() => {
    if (firstRender.current) { firstRender.current = false; return; }
    const main = mainRef.current;
    if (!main) return;
    main.scrollTop = 0;
    main.focus({ preventScroll: true });
    setMobileOpen(false);
  }, [pathname]);
  useEffect(() => {
    if (!mobileOpen) return;
    const esc = (e: KeyboardEvent) => e.key === "Escape" && setMobileOpen(false);
    window.addEventListener("keydown", esc);
    return () => window.removeEventListener("keydown", esc);
  }, [mobileOpen]);
  const skipToContent = (e: MouseEvent<HTMLAnchorElement>) => { e.preventDefault(); mainRef.current?.focus(); };

  return (
    <div className={`shell${collapsed ? " is-collapsed" : ""}${mobileOpen ? " mobile-nav-open" : ""}`}>
      <a className="skip-link" href="#main" onClick={skipToContent}>{t("nav.skip")}</a>
      <AnimatePresence>
        {mobileOpen && (
          <motion.button
            key="scrim"
            type="button"
            className="rail-scrim"
            aria-label={t("nav.close_menu")}
            onClick={() => setMobileOpen(false)}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
          />
        )}
      </AnimatePresence>
      <aside className="rail" aria-label={t("nav.label")}>
        <Link to={user ? homeFor(user.role) : "/dashboard"} className="brand" title={collapsed ? t("app.name") : undefined}>
          <BrandMark />
          <span className="brand-copy"><b>{t("app.name")}</b><span>{t("app.region")}</span></span>
        </Link>
        <nav className="nav-links" aria-label={t("nav.label")}>
          {groups.map((g) => {
            const items = visible.filter((n) => g.items.includes(n.to)).sort((x, y) => g.items.indexOf(x.to) - g.items.indexOf(y.to));
            if (!items.length) return null;
            return (
              <section className="nav-group" key={g.key} aria-label={t(g.key)}>
                <p className="nav-group-label" aria-hidden="true">{t(g.key)}</p>
                {items.map((n) => {
                  const I = n.icon;
                  return (
                    <NavLink
                      key={n.to}
                      to={n.to}
                      title={collapsed ? t(label(n)) : undefined}
                      aria-label={collapsed ? t(label(n)) : undefined}
                      data-testid={`nav-${n.to.slice(1)}`}
                      className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}
                      onClick={() => setMobileOpen(false)}
                    >
                      <I className="nav-icon" aria-hidden="true" />
                      <span>{t(label(n))}</span>
                      {n.to === "/inbox" && unacknowledged > 0 && <span className="nav-count" aria-label={t("inbox.count_label", { count: unacknowledged })}>{unacknowledged}</span>}
                    </NavLink>
                  );
                })}
              </section>
            );
          })}
        </nav>
        <ScreenStatus />
      </aside>
      <div className="workspace">
        <header className="topbar">
          <div className="topbar-left">
            <button type="button" className="rail-toggle desktop-toggle" aria-label={collapsed ? t("nav.expand") : t("nav.collapse")} title={collapsed ? t("nav.expand") : t("nav.collapse")} onClick={() => setCollapsed((v) => !v)}>
              {collapsed ? <PanelLeftOpen className="nav-icon" aria-hidden="true" /> : <PanelLeftClose className="nav-icon" aria-hidden="true" />}
            </button>
            <button type="button" className="rail-toggle mobile-toggle" aria-label={t("nav.open_menu")} aria-expanded={mobileOpen} onClick={() => setMobileOpen(true)}>
              <Menu className="nav-icon" aria-hidden="true" />
            </button>
            <nav className="topbar-context" aria-label={t("nav.breadcrumb")}>
              {group && <><span className="breadcrumb-root">{t(group.key)}</span><span className="breadcrumb-sep" aria-hidden="true">/</span></>}
              <p className="topbar-page-title" aria-current="page">{active ? t(label(active)) : t("app.name")}</p>
            </nav>
          </div>
          <div className="topbar-tools">
            <GlobalSearch pages={pages} />
            <Link
              to="/inbox"
              className="icon-action notification-action"
              aria-label={unacknowledged > 0 ? `${t("nav.inbox")}, ${t("inbox.count_label", { count: unacknowledged })}` : t("nav.inbox")}
              title={t("nav.inbox")}
            >
              <Inbox className="nav-icon" aria-hidden="true" />
              {unacknowledged > 0 && <span className="notification-dot" aria-hidden="true" data-count={unacknowledged > 9 ? "9+" : String(unacknowledged)} />}
            </Link>
            <button className="utility-button language-button" onClick={toggleLanguage} lang={i18n.language === "te" ? "en" : "te"} title={t("nav.switch_language")}>
              <Languages size={15} aria-hidden="true" />{i18n.language === "te" ? "English" : "తెలుగు"}
            </button>
            <ProfileMenu />
          </div>
        </header>
        <main className="main" id="main" ref={mainRef} tabIndex={-1} data-admin={isAdmin(user) || undefined}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
