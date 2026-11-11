import { useEffect, useRef, type MouseEvent } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../auth";
import { DemoBand } from "../demo";

const NAV: { to: string; key: string; roles: string[] }[] = [
  { to: "/alerts", key: "nav.queue", roles: ["analyst", "reviewer", "nodal_officer", "legal_officer", "senior_officer", "admin", "auditor"] },
  { to: "/assets", key: "nav.assets", roles: ["admin", "nodal_officer", "analyst", "legal_officer"] },
  { to: "/records", key: "nav.records", roles: ["admin", "legal_officer", "nodal_officer", "analyst"] },
  { to: "/monthly", key: "nav.monthly", roles: ["senior_officer", "nodal_officer", "legal_officer", "admin", "auditor"] },
  { to: "/audit", key: "nav.audit", roles: ["auditor", "admin"] },
];

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
      <DemoBand />
      <nav className="rail" aria-label={t("nav.label")}>
        <div className="brand">
          <Mark />
          <b>{t("app.name")}</b>
          <span className="small">{t("app.tagline")}</span>
        </div>
        {NAV.filter((n) => user && n.roles.includes(user.role)).map((n) => (
          <NavLink key={n.to} to={n.to}>
            {t(n.key)}
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
