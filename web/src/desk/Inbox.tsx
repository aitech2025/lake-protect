import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { api, fmtDateTime, type Note } from "../api";
import { useAsync, usePageTitle } from "../components/Bits";
import { EmptyState, PageState } from "../components/PageState";
import { notifyCountChanged } from "../components/Layout";
import { Segmented } from "../components/Segmented";
import { Inbox as InboxIcon } from "lucide-react";

const KIND_CLASS: Record<Note["kind"], string> = {
  incident_opened: "review",
  citizen_report: "field",
  satellite_review: "field",
  reminder: "legal",
  not_acknowledged: "legal",
  incident_decided: "officer",
  weekly_digest: "field",
  incident_assigned: "review",
  field_reported: "field",
  recommended: "watch",
  returned: "legal",
};

/** Notifications to this person (DECISIONS.md D-059): what needs acknowledging first, then the rest. */
export function Inbox() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language;
  const [pending, setPending] = useState(true);
  const [busy, setBusy] = useState<number | null>(null);
  const [failure, setFailure] = useState<string | null>(null);
  const { data, error, status, loading, reload } = useAsync(
    () => api<{ items: Note[]; unacknowledged: number }>(`/notifications${pending ? "?pending=true" : ""}`),
    [pending],
  );
  usePageTitle(t("inbox.title"));

  const ack = async (n: Note) => {
    setBusy(n.id);
    setFailure(null);
    try {
      await api(`/notifications/${n.id}/ack`, { method: "POST" });
      notifyCountChanged();
      reload();
    } catch (e) {
      setFailure(String((e as Error).message));
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="page inbox" data-testid="inbox">
      <div className="page-head">
        <div>
          <h1>{t("inbox.title")}</h1>
          <p className="muted">{data ? t("inbox.lede", { count: data.unacknowledged }) : " "}</p>
        </div>
        <Segmented
          label={t("inbox.show")}
          value={pending ? "pending" : "all"}
          onChange={(v) => setPending(v === "pending")}
          options={[
            { value: "pending", label: t("inbox.pending"), testId: "inbox-pending" },
            { value: "all", label: t("inbox.all"), testId: "inbox-all" },
          ]}
        />
      </div>
      {failure && <p className="banner stop" role="alert">{failure}</p>}
      <PageState loading={loading && !data} error={error} status={status} onRetry={reload} />
      {data && data.items.length === 0 && (
        <EmptyState icon={<InboxIcon aria-hidden="true" />} title={pending ? t("inbox.empty_pending") : t("inbox.empty")}>
          {pending && <button type="button" className="btn quiet" onClick={() => setPending(false)}>{t("inbox.show_all")}</button>}
        </EmptyState>
      )}
      <ul className="notes" data-testid="notes">
        {data?.items.map((n) => (
          <li key={n.id} className={`note-card${n.needs_ack && !n.acknowledged_at ? " needs" : ""}`} data-testid={`note-${n.kind}`} data-alert-id={n.alert_id ?? undefined}>
            <div className="note-head">
              <span className={`pill ${KIND_CLASS[n.kind]}`}>{t(`inbox.kind.${n.kind}`)}</span>
              <span className="small muted">{fmtDateTime(n.created_at, lang)}</span>
            </div>
            <h3>{n.subject}</h3>
            <p className="note-body" tabIndex={0}>{n.body}</p>
            <div className="note-foot">
              {n.alert_id && <Link to={`/alerts/${n.alert_id}`} className={n.kind === "incident_assigned" || n.kind === "recommended" || n.kind === "field_reported" ? "btn" : "btn secondary"} data-testid="note-open">{t("inbox.open_incident")}</Link>}
              {n.report_id && <Link to={`/reports/${n.report_id}`} className="btn secondary" data-testid="note-open-report">{t("inbox.open_report")}</Link>}
              {n.kind === "weekly_digest" && <Link to="/dashboard" className="btn secondary">{t("inbox.open_overview")}</Link>}
              {n.needs_ack && !n.acknowledged_at && (
                <button className="btn" disabled={busy === n.id} onClick={() => void ack(n)} data-testid="note-ack">{t("inbox.ack")}</button>
              )}
              {n.acknowledged_at && (
                <span className="small ok" data-testid="note-acked">{t("inbox.acked", { date: fmtDateTime(n.acknowledged_at, lang), via: t(`inbox.via.${n.ack_via}`) })}</span>
              )}
              <span className="deliveries">
                {n.deliveries.map((d) => (
                  <span key={d.channel} className={`delivery ${d.status}`} title={d.detail ?? undefined} data-testid={`delivery-${d.channel}`}>
                    {t(`inbox.channel.${d.channel}`)}: {t(`inbox.status.${d.status}`)}
                  </span>
                ))}
              </span>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** On an incident: "you were told about this"; acknowledging here, or acting on it, clears it. */
export function AckBanner({ notes, isAdminUser, onDone }: { notes: { id: number; kind: string; created_at: string }[]; isAdminUser: boolean; onDone: () => void }) {
  const { t, i18n } = useTranslation();
  const [busy, setBusy] = useState(false);
  if (!notes.length) return null;
  const ack = async () => {
    setBusy(true);
    try {
      await api(`/notifications/${notes[0].id}/ack`, { method: "POST" });
      notifyCountChanged();
      onDone();
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="banner info ack-banner" data-testid="ack-banner">
      <span>
        {t("inbox.banner", { date: fmtDateTime(notes[0].created_at, i18n.language) })}{" "}
        {notes.some((n) => n.kind === "reminder") ? t("inbox.banner_reminded") + " " : ""}
        {isAdminUser ? t("inbox.banner_admin") : t("inbox.banner_viewer")}
      </span>
      <button className="btn secondary" disabled={busy} onClick={() => void ack()} data-testid="ack-banner-button">{t("inbox.ack")}</button>
    </div>
  );
}
