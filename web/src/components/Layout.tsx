import { useEffect, useRef, useState, type MouseEvent } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api } from "../api";
import { useAuth } from "../auth";

// Both roles see every page (D-057); what each may change is decided by the server. The Officials
// page holds people's contact details, so only the admin has it (D-059).
const BOTH = ["admin", "viewer"];
const NAV: { to: string; key: string; roles: string[] }[] = [
  { to: "/dashboard", key: "nav.dashboard", roles: BOTH },
  { to: "/inbox", key: "nav.inbox", roles: BOTH },
  { to: "/alerts", key: "nav.queue", roles: BOTH },
  { to: "/reports", key: "nav.reports", roles: BOTH },
  { to: "/assets", key: "nav.assets", roles: BOTH },
  { to: "/records", key: "nav.records", roles: BOTH },
  { to: "/sources", key: "nav.sources", roles: BOTH },
  { to: "/satellites", key: "nav.satellites", roles: BOTH },
  { to: "/monthly", key: "nav.monthly", roles: BOTH },
  { to: "/audit", key: "nav.audit", roles: BOTH },
  { to: "/officials", key: "nav.officials", roles: ["admin"] },
];

const COUNT_EVENT = "lp:notify-count";

/** Pages that acknowledge a notification call this, so the side bar's count updates at once. */
export function notifyCountChanged(): void {
  window.dispatchEvent(new Event(COUNT_EVENT));
}

/** How many notifications wait for this person's acknowledgement. */
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
    return () => {
      live = false;
    };
  }, [user, pathname, tick]);
  return n;
}

export function Mark() {
  // Lake outline with a solid boundary and a dashed buffer: the product's own line language.
  return (
    <svg width="40" height="28" viewBox="0 0 40 28" aria-hidden="true">
      <path d="M6 15c0-6 6-10 13-10s15 3 15 9-6 10-14 10S6 21 6 15z" fill="#7fb6dd" stroke="#fff" strokeWidth="2" />
      <path d="M2 15c0-8 8-13 17-13s19 4 19 12-8 13-18 13S2 23 2 15z" fill="none" stroke="#e98a7c" strokeWidth="1.5" strokeDasharray="3 2.5" />
    </svg>
  );
}

export function Layout() {
  const { t, i18n } = useTranslation();
  const { user, logout } = useAuth();
  const { pathname } = useLocation();
  const unacknowledged = useUnacknowledged();
  const mainRef = useRef<HTMLElement>(null);
  const firstRender = useRef(true);
  const toggle = () => void i18n.changeLanguage(i18n.language === "te" ? "en" : "te");

  // After moving to another page, start keyboard and screen-reader users at the new content,
  // not wherever focus was on the old page (UI audit A4).
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
    <div className="shell">
      <a className="skip-link" href="#main" onClick={skipToContent}>{t("nav.skip")}</a>
      <nav className="rail" aria-label={t("nav.label")}>
        <div className="brand">
          <Mark />
          <b>{t("app.name")}</b>
          <span className="small">{t("app.tagline")}</span>
        </div>
        {NAV.filter((n) => user && n.roles.includes(user.role)).map((n) => (
          <NavLink key={n.to} to={n.to} data-testid={`nav-${n.to.slice(1)}`}>
            {t(n.key)}
            {n.to === "/inbox" && unacknowledged > 0 && (
              <span className="nav-count" data-testid="inbox-count" aria-label={t("inbox.count_label", { count: unacknowledged })}>{unacknowledged}</span>
            )}
          </NavLink>
        ))}
        <div className="who">
          <b>{user?.name}</b>
          {user && t(`role.${user.role}`)}
          <div>
            <button onClick={toggle} lang={i18n.language === "te" ? "en" : "te"}>{t("nav.language")}</button>
            <button onClick={logout}>{t("nav.logout")}</button>
          </div>
        </div>
      </nav>
      <main className="main" id="main" ref={mainRef} tabIndex={-1}>
        <Outlet />
      </main>
    </div>
  );
}
