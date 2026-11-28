/* eslint-disable @typescript-eslint/no-explicit-any */
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { api, fmtDateTime } from "../api";
import { useAuth } from "../auth";
import { useAsync, usePageTitle } from "../components/Bits";
import { PageState, TableRegion } from "../components/PageState";

type Person = {
  id: number; username: string; name: string; role: string; language: string; email: string | null; phone: string | null;
  channels: string[]; areas: { district: string; mandal: string | null }[]; unacknowledged: number;
};
type KnownArea = { district: string; assets: number; mandals: { mandal: string; assets: number }[] };
const OUTSIDE = ["email", "sms", "whatsapp"] as const;

/** Admin only (DECISIONS.md D-059): who covers which area, how each is reached, and what was delivered. */
export function Officials() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const people = useAsync(() => api<Person[]>("/users"), []);
  const areas = useAsync(() => api<{ items: KnownArea[] }>("/areas"), []);
  const log = useAsync(() => api<any>("/notifications/deliveries?limit=150"), []);
  const [message, setMessage] = useState<string | null>(null);
  usePageTitle(t("officials.title"));

  const run = async (path: string, json?: unknown) => {
    setMessage(null);
    try {
      const out = await api<any>(path, { method: "POST", json });
      const deliveries = Object.values(out.deliveries ?? {}).reduce((a: number, b) => a + Number(b), 0);
      if (path.endsWith("digests")) setMessage(t(out.sent ? "officials.digest_sent" : "officials.digest_already", { n: out.sent, week: out.week }));
      else setMessage(t("officials.ran", { n: deliveries }));
      log.reload();
    } catch (e) {
      setMessage(String((e as Error).message));
    }
  };

  return (
    <div className="page officials" data-testid="officials">
      <div className="page-head">
        <div>
          <h1>{t("officials.title")}</h1>
          <p className="muted">{t("officials.lede")}</p>
        </div>
        <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
          <button className="btn secondary" onClick={() => void run("/notifications/run")} data-testid="run-outbox">{t("officials.run")}</button>
          <button className="btn" onClick={() => void run("/notifications/digests", {})} data-testid="send-digest">{t("officials.digest")}</button>
        </div>
      </div>
      {message && <p className="banner info" role="status" data-testid="officials-message">{message}</p>}

      <section className="channel-grid" aria-label={t("officials.channels")} data-testid="channels">
        {(log.data?.channels ?? []).map((c: any) => (
          <div key={c.channel} className={`panel channel ${c.ready ? "ready" : "held"}`} data-testid={`channel-${c.channel}`}>
            <h2 className="title-s">{t(`inbox.channel.${c.channel}`)}</h2>
            <p className={c.ready ? "ok" : "flag"}>{c.ready ? t("officials.ready") : t("officials.held")}</p>
            <p className="small muted">{c.detail}</p>
          </div>
        ))}
      </section>

      <h2 className="title-s" style={{ margin: "1.25rem 0 0.5rem" }}>{t("officials.people")}</h2>
      <PageState loading={people.loading && !people.data} error={people.error} status={people.status} onRetry={people.reload} />
      <div className="people">
        {people.data?.map((p) => <PersonCard key={`${p.id}-${p.role}`} p={p} known={areas.data?.items ?? []} onSaved={people.reload} self={p.id === user?.id} />)}
      </div>

      <h2 className="title-s" style={{ margin: "1.5rem 0 0.5rem" }}>{t("officials.log")}</h2>
      {log.data && (
        <p className="small muted" style={{ marginBottom: "0.5rem" }} data-testid="log-totals">
          {log.data.totals.map((x: any) => `${t(`inbox.channel.${x.channel}`)} ${t(`inbox.status.${x.status}`)}: ${x.n}`).join(" · ")}
        </p>
      )}
      <PageState loading={log.loading && !log.data} error={log.error} status={log.status} onRetry={log.reload} />
      {log.data && (
        <TableRegion label={t("officials.log")}>
          <table className="grid" data-testid="delivery-log">
            <thead>
              <tr>
                <th>{t("officials.col.when")}</th><th>{t("officials.col.to")}</th><th>{t("officials.col.what")}</th>
                <th>{t("officials.col.channel")}</th><th>{t("officials.col.status")}</th><th>{t("officials.col.detail")}</th><th>{t("officials.col.ack")}</th>
              </tr>
            </thead>
            <tbody>
              {log.data.items.map((r: any, i: number) => (
                <tr key={`${r.id}-${r.channel ?? "app"}-${i}`}>
                  <td>{fmtDateTime(r.created_at)}</td>
                  <td>{r.user_name}{r.to_masked ? <div className="small muted">{r.to_masked}</div> : null}</td>
                  <td>
                    {r.alert_id ? <Link to={`/alerts/${r.alert_id}`}>{r.subject}</Link> : r.subject}
                    <div className="small muted">{t(`inbox.kind.${r.kind}`)}</div>
                  </td>
                  <td>{r.channel ? t(`inbox.channel.${r.channel}`) : t("inbox.channel.in_app")}</td>
                  <td>{r.status ? <span className={`delivery ${r.status}`}>{t(`inbox.status.${r.status}`)}</span> : t("inbox.status.sent")}</td>
                  <td className="small">{r.detail ?? ""}</td>
                  <td className="small">{r.needs_ack ? (r.acknowledged_at ? fmtDateTime(r.acknowledged_at) : <b className="flag">{t("officials.not_yet")}</b>) : "–"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableRegion>
      )}
    </div>
  );
}

const ROLES = ["admin", "senior_official", "district_officer", "field_officer"] as const;
const AREA_ROLES = ["district_officer", "field_officer"];

function PersonCard({ p, known, onSaved, self }: { p: Person; known: KnownArea[]; onSaved: () => void; self: boolean }) {
  const { t } = useTranslation();
  const [role, setRole] = useState(p.role);
  const [email, setEmail] = useState(p.email ?? "");
  const [phone, setPhone] = useState(p.phone ?? "");
  const [channels, setChannels] = useState<string[]>(p.channels);
  const [list, setList] = useState(p.areas);
  const [district, setDistrict] = useState("");
  const [mandal, setMandal] = useState("");
  const [note, setNote] = useState<string | null>(null);
  const isViewer = AREA_ROLES.includes(role);
  const mandals = known.find((k) => k.district === district)?.mandals ?? [];

  const save = async () => {
    setNote(null);
    try {
      await api(`/users/${p.id}`, {
        method: "PATCH",
        json: { ...(role !== p.role ? { role } : {}), email: email || undefined, phone: phone || undefined, channels, clear: [...(email ? [] : ["email"]), ...(phone ? [] : ["phone"])] },
      });
      if (isViewer) await api(`/users/${p.id}/areas`, { method: "PUT", json: { areas: list } });
      setNote(t("officials.saved"));
      onSaved();
    } catch (e) {
      setNote(String((e as Error).message));
    }
  };
  const toggle = (c: string) => setChannels((cs) => (cs.includes(c) ? cs.filter((x) => x !== c) : [...cs, c]));
  const add = () => {
    if (!district) return;
    setList((l) => [...l, { district, mandal: mandal || null }]);
    setDistrict("");
    setMandal("");
  };

  return (
    <div className="panel person" data-testid={`person-${p.username}`}>
      <div className="person-head">
        <div>
          <h3>{p.name}</h3>
          <span className="small muted">{p.language === "te" ? "తెలుగు" : "English"} · <span className="mono">{p.username}</span></span>
        </div>
        {p.unacknowledged > 0 && <span className="pill review">{t("officials.unacked", { n: p.unacknowledged })}</span>}
      </div>
      <div className="person-grid">
        <label className="field wide-field">{t("officials.persona")}
          <select value={role} onChange={(e) => setRole(e.target.value)} disabled={self} data-testid="person-role">
            {ROLES.map((r) => <option key={r} value={r}>{t(`role.${r}`)}</option>)}
          </select>
          <small>{self ? t("officials.persona_self") : t(`role_help.${role}`)}</small>
        </label>
        <label className="field">{t("officials.email")}<input type="email" value={email} onChange={(e) => setEmail(e.target.value)} data-testid="person-email" /></label>
        <label className="field">{t("officials.phone")}<input value={phone} placeholder="+91…" onChange={(e) => setPhone(e.target.value)} data-testid="person-phone" /></label>
        <fieldset className="field channels-field">
          <legend>{t("officials.channels_for")}</legend>
          <label><input type="checkbox" checked disabled /> {t("inbox.channel.in_app")}</label>
          {OUTSIDE.map((c) => (
            <label key={c}><input type="checkbox" checked={channels.includes(c)} onChange={() => toggle(c)} data-testid={`person-${c}`} /> {t(`inbox.channel.${c}`)}</label>
          ))}
        </fieldset>
      </div>
      <div className="person-areas">
        <b className="small">{t("officials.areas")}</b>
        {!isViewer ? (
          <p className="small muted">{t("officials.statewide")}</p>
        ) : (
          <>
            <div className="chips" data-testid="person-areas">
              {list.length === 0 && <span className="small flag">{t("officials.no_areas")}</span>}
              {list.map((a, i) => (
                <span key={`${a.district}/${a.mandal}`} className="chip area-chip">
                  {a.mandal ? `${a.mandal}, ${a.district}` : a.district}
                  <button type="button" aria-label={t("officials.remove", { area: a.mandal ?? a.district })} onClick={() => setList((l) => l.filter((_, j) => j !== i))}>×</button>
                </span>
              ))}
            </div>
            <div className="area-add">
              <select value={district} onChange={(e) => { setDistrict(e.target.value); setMandal(""); }} aria-label={t("officials.district")} data-testid="area-district">
                <option value="">{t("officials.district")}</option>
                {known.map((k) => <option key={k.district} value={k.district}>{k.district} ({k.assets})</option>)}
              </select>
              <select value={mandal} onChange={(e) => setMandal(e.target.value)} disabled={!district} aria-label={t("officials.mandal")} data-testid="area-mandal">
                <option value="">{t("officials.whole_district")}</option>
                {mandals.map((m) => <option key={m.mandal} value={m.mandal}>{m.mandal} ({m.assets})</option>)}
              </select>
              <button type="button" className="btn secondary" onClick={add} disabled={!district} data-testid="area-add">{t("officials.add_area")}</button>
            </div>
          </>
        )}
      </div>
      <div className="person-foot">
        <button className="btn" onClick={() => void save()} data-testid="person-save">{t("officials.save")}</button>
        {note && <span className="small" role="status">{note}</span>}
      </div>
    </div>
  );
}
