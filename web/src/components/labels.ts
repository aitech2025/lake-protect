/** Incident states (DECISIONS.md D-057), and the colour each uses on maps and in lists. */
export const STATES = ["OPEN", "UNDER_REVIEW", "CONFIRMED", "DISMISSED", "CLOSED"] as const;

export const GROUP_OF: Record<string, string> = {
  OPEN: "open",
  UNDER_REVIEW: "review",
  CONFIRMED: "confirmed",
  DISMISSED: "dismissed",
  CLOSED: "closed",
};

export const GROUP_COLOUR: Record<string, string> = {
  open: "#c94b4b",
  review: "#167c80",
  confirmed: "#27845a",
  dismissed: "#64748b",
  closed: "#8795a2",
};

/** What changed, in the order officials name it. */
export const CHANGE_TYPES = ["building", "soil_fill", "levelling", "clearing"] as const;

export const CONFIRMED_STATUSES = ["physically_marked", "final_notification", "surveyed_agency"];

export function certainty(status: string | null | undefined): "confirmed" | "preliminary" | "estimated" {
  if (status && CONFIRMED_STATUSES.includes(status)) return "confirmed";
  if (status === "preliminary_notification") return "preliminary";
  return "estimated";
}
