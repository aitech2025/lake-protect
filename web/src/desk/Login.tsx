import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { api, type User } from "../api";
import { homeFor, useAuth } from "../auth";
import { Mark } from "../components/Layout";
import { DemoBand, useDemoOnScreen } from "../demo";

export function Login() {
  const { t, i18n } = useTranslation();
  const { login } = useAuth();
  const nav = useNavigate();
  const [users, setUsers] = useState<User[]>([]);
  const [error, setError] = useState<string | null>(null);
  useDemoOnScreen(users.length > 0);

  useEffect(() => {
    api<User[]>("/auth/demo-users").then(setUsers).catch((e: Error) => setError(e.message));
  }, []);

  const go = async (username: string) => {
    try {
      const u = await login(username);
      nav(homeFor(u.role));
    } catch (e) {
      setError((e as Error).message);
    }
  };

  return (
    <>
      <DemoBand />
      <div className="login">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "1rem" }}>
          <div style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
            <span style={{ background: "#1c2b33", borderRadius: 6, padding: 6, display: "inline-flex" }}><Mark /></span>
            <div>
              <h1>{t("app.name")}</h1>
              <p className="muted">{t("app.tagline")}</p>
            </div>
          </div>
          <button className="btn secondary" onClick={() => void i18n.changeLanguage(i18n.language === "te" ? "en" : "te")}>{t("nav.language")}</button>
        </div>
        <h2 style={{ marginTop: "2.5rem" }}>{t("login.title")}</h2>
        <p className="muted">{t("login.intro")}</p>
        {error && <p className="error">{t("error.load", { msg: error })}</p>}
        <div className="roles">
          {users.map((u) => (
            <button key={u.id} onClick={() => void go(u.username)} data-testid={`login-${u.username}`}>
              <b>{t(`role.${u.role}`)}</b>
              <span className="small muted">{u.name}</span>
              <span className="small">{t(`login.role.${u.role}`)}</span>
            </button>
          ))}
        </div>
      </div>
    </>
  );
}
