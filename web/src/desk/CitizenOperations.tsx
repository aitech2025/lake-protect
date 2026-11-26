import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api, fmtDateTime } from "../api";
import { isAdmin, useAuth } from "../auth";
import { useAsync, usePageTitle } from "../components/Bits";
import { PageState } from "../components/PageState";

type Review = {
  id: number; alert_id: number; alert_code: string | null; report_ref: string | null; kind: string;
  requested_at: string | null; attempts: number; max_attempts: number; look_date: string | null; detail: string | null;
};
type Operations = {
  satellite_reviews: { pending: number; items: Review[]; max_items: number };
  outbound_messages: { by_channel_status: { channel: string; status: string; count: number; last_at: string | null }[]; retry_pending: number; retry_exhausted: number };
  outbound_channels: { channel: string; ready: boolean; mode: string; detail: string }[];
  citizen_updates: { sms_updates: boolean; whatsapp: boolean };
  whatsapp_inbound: { ready: boolean; mode: string; detail: string };
};

export function CitizenOperations() {
  const { t, i18n } = useTranslation();
  const { user } = useAuth();
  const { data, error, status, loading, reload } = useAsync(() => api<Operations>("/citizen/operations"), []);
  usePageTitle(t("citizen_ops.title"));

  if (!isAdmin(user)) {
    return <div className="page"><h1>{t("citizen_ops.title")}</h1><p className="banner warn">{t("citizen_ops.admin_only")}</p></div>;
  }

  const channels = data?.outbound_channels ?? [];
  return (
    <div className="page" data-testid="citizen-operations">
      <div className="page-head">
        <div><h1>{t("citizen_ops.title")}</h1><p className="muted">{t("citizen_ops.lede")}</p></div>
        <button type="button" className="btn secondary" onClick={reload} data-testid="citizen-ops-refresh">{t("citizen_ops.refresh")}</button>
      </div>
      <PageState loading={loading && !data} error={error} status={status} onRetry={reload} />
      {data && (
        <>
          <section className="kinds-strip" aria-label={t("citizen_ops.health")}>
            <div className="kind-card"><b>{t("citizen_ops.pending_reviews")}</b><span className="small muted" data-testid="pending-review-count">{data.satellite_reviews.pending}</span></div>
            <div className="kind-card"><b>{t("citizen_ops.retry_pending")}</b><span className="small muted">{data.outbound_messages.retry_pending}</span></div>
            <div className="kind-card"><b>{t("citizen_ops.retry_exhausted")}</b><span className="small muted">{data.outbound_messages.retry_exhausted}</span></div>
            <div className="kind-card"><b>{t("citizen_ops.sms_updates")}</b><span className={data.citizen_updates.sms_updates ? "ok" : "flag"}>{t(data.citizen_updates.sms_updates ? "citizen_ops.configured" : "citizen_ops.disabled")}</span></div>
            <div className="kind-card"><b>{t("citizen_ops.whatsapp_updates")}</b><span className={data.citizen_updates.whatsapp ? "ok" : "flag"}>{t(data.citizen_updates.whatsapp ? "citizen_ops.configured" : "citizen_ops.disabled")}</span></div>
            <div className="kind-card"><b>{t("citizen_ops.whatsapp_inbound")}</b><span className={data.whatsapp_inbound.ready ? "ok" : "flag"}>{t(data.whatsapp_inbound.ready ? "citizen_ops.configured" : "citizen_ops.disabled")}</span><span className="small muted">{data.whatsapp_inbound.detail}</span></div>
          </section>
          <section className="section" data-testid="citizen-review-queue">
            <h2>{t("citizen_ops.review_queue")}</h2>
            {data.satellite_reviews.items.length === 0 ? <p className="muted">{t("citizen_ops.no_pending_reviews")}</p> : (
              <div className="list">
                {data.satellite_reviews.items.map((r) => (
                  <div className="row" key={r.id}>
                    <span className="bar" />
                    <span>
                      <b>{r.alert_code ?? t("citizen_ops.review")} · {r.report_ref ?? ""}</b>
                      <span className="meta">
                        <span>{t("citizen_ops.attempts", { n: r.attempts, max: r.max_attempts })}</span>
                        <span>{r.kind}</span>
                        {r.requested_at && <span>{fmtDateTime(r.requested_at, i18n.language)}</span>}
                        {r.look_date && <span>{t("citizen_ops.look_date", { date: r.look_date })}</span>}
                      </span>
                      {r.detail && <span className="small muted">{r.detail}</span>}
                    </span>
                    <Link className="btn secondary" to={`/alerts/${r.alert_id}`}>{t("citizen_ops.open_incident")}</Link>
                  </div>
                ))}
              </div>
            )}
          </section>
          <section className="section" data-testid="citizen-message-queue">
            <h2>{t("citizen_ops.outbound_queue")}</h2>
            {data.outbound_messages.by_channel_status.length === 0 ? <p className="muted">{t("citizen_ops.no_outbound")}</p> : (
              <table className="grid">
                <thead><tr><th>{t("citizen_ops.channel")}</th><th>{t("citizen_ops.delivery_status")}</th><th>{t("citizen_ops.count")}</th><th>{t("citizen_ops.last_attempt")}</th></tr></thead>
                <tbody>{data.outbound_messages.by_channel_status.map((row) => (
                  <tr key={row.channel + row.status}>
                    <td>{row.channel}</td><td>{row.status}</td><td>{row.count}</td><td>{row.last_at ? fmtDateTime(row.last_at, i18n.language) : "—"}</td>
                  </tr>
                ))}</tbody>
              </table>
            )}
          </section>
          <section className="section" data-testid="citizen-channel-readiness">
            <h2>{t("citizen_ops.channel_readiness")}</h2>
            {channels.map((channel) => (
              <p key={channel.channel} className="row">
                <b>{channel.channel}</b>
                <span className={channel.ready ? "ok" : "flag"}>{t(channel.ready ? "citizen_ops.ready" : "citizen_ops.disabled")}</span>
                <span className="small muted">{channel.detail}</span>
              </p>
            ))}
          </section>
        </>
      )}
    </div>
  );
}
