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
          <p>{status === 403 ? t("error.forbidden") : t("error.not_found")}</p>
          <Link to={home}>{t("error.home")}</Link>
        </div>
      );
    }
    return (
      <div className="page-state banner stop" role="alert" data-state-kind="error">
        <p>{t("error.load", { msg: error })}</p>
        {onRetry && <button type="button" className="btn secondary" onClick={onRetry}>{t("error.retry")}</button>}
      </div>
    );
  }
  if (loading) return <p className="page-state loading" role="status" data-state-kind="loading">{t("error.loading")}</p>;
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
