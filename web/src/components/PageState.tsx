import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { homeFor, useAuth } from "../auth";

type Props = { loading?: boolean; error?: string | null; status?: number | null; onRetry?: () => void };

/**
 * One way to say "loading", "not allowed", "not found" and "failed", so none of them looks like
 * an empty page (UI audit A1). Renders nothing once the data is there.
 * The server stays the authority on access: a 403 is shown as such, never hidden.
 */
export function PageState({ loading, error, status, onRetry }: Props) {
  const { t } = useTranslation();
  const { user } = useAuth();
  const home = user ? homeFor(user.role) : "/login";
  if (error) {
    if (status === 403 || status === 404) {
      return (
        <div className="page-state" role="alert" data-state-kind={status === 403 ? "forbidden" : "not-found"}>
          <h2>{status === 403 ? t("error.forbidden") : t("error.not_found")}</h2>
          <Link to={home} className="btn secondary">{t("error.home")}</Link>
        </div>
      );
    }
    return (
      <div className="page-state banner stop" role="alert" data-state-kind="error">
        <h2>{t("error.load", { msg: error })}</h2>
        {onRetry && <button type="button" className="btn secondary" onClick={onRetry}>{t("error.retry")}</button>}
      </div>
    );
  }
  if (loading) {
    return (
      <div className="page-state loading" role="status" data-state-kind="loading">
        <span className="sr-only">{t("error.loading")}</span>
        <span className="skeleton" style={{ width: "62%" }} aria-hidden="true" />
        <span className="skeleton" style={{ width: "88%" }} aria-hidden="true" />
        <span className="skeleton" style={{ width: "74%" }} aria-hidden="true" />
      </div>
    );
  }
  return null;
}

/** A data table that scrolls sideways inside its own labelled region on narrow screens (UI audit A3). */
export function TableRegion({ label, children }: { label: string; children: ReactNode }) {
  return (
    // A scrollable region must be reachable by keyboard to be scrolled without a mouse.
    // eslint-disable-next-line jsx-a11y/no-noninteractive-tabindex
    <div className="table-scroll" role="region" aria-label={label} tabIndex={0}>
      {children}
    </div>
  );
}

/** An empty list: says what is missing and, when there is one, the next step. */
export function EmptyState({ icon, title, children }: { icon?: ReactNode; title: string; children?: ReactNode }) {
  return (
    <div className="empty-state">
      {icon}
      <b>{title}</b>
      {children}
    </div>
  );
}
