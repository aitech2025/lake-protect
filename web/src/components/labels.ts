/** How states group for people, and the colour each group uses on maps and in lists. */
export const GROUP_OF: Record<string, string> = {
  CANDIDATE: "review",
  TRIAGE: "review",
  CONFIRMED: "review",
  ASSIGNED: "field",
  FIELD_CONFIRMED: "field",
  AWAITING_BOUNDARY: "field",
  HOLD_LEGAL: "legal",
  PACK_READY: "officer",
  WITH_OFFICER: "officer",
  ACTION_RECORDED: "officer",
  POST_ACTION_WATCH: "officer",
  WATCH_LIST: "watch",
  CLOSED_OUT_OF_SCOPE: "closed",
  CLOSED_LEGACY: "closed",
  CLOSED_AUTHORISED: "closed",
  CLOSED_NOT_REAL: "closed",
  CLOSED_FALSE_ALARM: "closed",
  CLOSED_NO_ACTION: "closed",
};

export const GROUP_COLOUR: Record<string, string> = {
  review: "#b07219",
  field: "#1f6fa8",
  legal: "#c4402f",
  officer: "#2d7a57",
  watch: "#6b5a91",
  closed: "#8a979d",
};

export const CONFIRMED_STATUSES = ["physically_marked", "final_notification", "surveyed_agency"];

export function certainty(status: string | null | undefined): "confirmed" | "preliminary" | "estimated" {
  if (status && CONFIRMED_STATUSES.includes(status)) return "confirmed";
  if (status === "preliminary_notification") return "preliminary";
  return "estimated";
}
