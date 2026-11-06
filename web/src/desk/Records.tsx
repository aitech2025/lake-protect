/* eslint-disable @typescript-eslint/no-explicit-any */
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { api, fmtDate } from "../api";
import { useAuth } from "../auth";
import { useAsync } from "../components/Bits";
import { DemoTag, useDemoOnScreen } from "../demo";

const KINDS = ["permits", "works", "court-cases"] as const;

export function Records() {
  const { t, i18n } = useTranslation();
  const { user } = useAuth();
  const [kind, setKind] = useState<(typeof KINDS)[number]>("permits");
  const [message, setMessage] = useState<string | null>(null);
  const { data, error, reload } = useAsync(() => api<{ items: any[]; has_demo: boolean }>(`/records/${kind}`), [kind]);
  useDemoOnScreen(Boolean(data?.has_demo));
  const canImport = user && ["admin", "legal_officer"].includes(user.role);

  const upload = async (file: File) => {
    const form = new FormData();
    form.append("file", file);
    try {
      const out = await api<any>(`/records/${kind}/import`, { body: form, method: "POST" });
      setMessage(`${t("records.imported", { n: out.imported })}${out.alerts_put_on_hold.length ? `. ${t("records.held", { n: out.alerts_put_on_hold.length })}` : ""}`);
      reload();
    } catch (e) {
      setMessage((e as Error).message);
    }
  };

  const cols: Record<string, [string, (r: any) => string][]> = {
    permits: [["ref", (r) => r.ref], ["source", (r) => r.source], ["kind", (r) => r.kind], ["from", (r) => fmtDate(r.valid_from, i18n.language)], ["to", (r) => fmtDate(r.valid_to, i18n.language)]],
    works: [["ref", (r) => r.ref], ["agency", (r) => r.agency], ["work", (r) => r.description], ["from", (r) => fmtDate(r.starts_on, i18n.language)], ["to", (r) => fmtDate(r.ends_on, i18n.language)]],
    "court-cases": [["case", (r) => r.case_no], ["court", (r) => r.court], ["status", (r) => r.status], ["hearing", (r) => fmtDate(r.next_hearing, i18n.language)]],
  };

  return (
    <div className="page">
      <div className="page-head">
        <h1>{t("records.title")}</h1>
        {canImport && (
          <label className="btn secondary">
            {t("records.import")}
            <input type="file" accept=".csv,text/csv" className="sr-only" onChange={(e) => e.target.files?.[0] && void upload(e.target.files[0])} />
          </label>
        )}
      </div>
      <div className="chips" style={{ marginBottom: "1rem" }}>
        {KINDS.map((k) => <button key={k} className="chip" aria-pressed={kind === k} onClick={() => setKind(k)}>{t(`records.${k}`)}</button>)}
      </div>
      {message && <p className="banner info" role="status" style={{ marginBottom: "1rem" }}>{message}</p>}
      {error && <p className="error">{t("error.load", { msg: error })}</p>}
      {data && data.items.length === 0 && <p className="muted">{t("records.empty")}</p>}
      {data && data.items.length > 0 && (
        <table className="grid">
          <thead><tr>{cols[kind].map(([h]) => <th key={h}>{t(`records.col.${h}`)}</th>)}<th /></tr></thead>
          <tbody>
            {data.items.map((r) => (
              <tr key={r.id}>{cols[kind].map(([h, f]) => <td key={h}>{f(r)}</td>)}<td>{r.is_demo && <DemoTag />}</td></tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
