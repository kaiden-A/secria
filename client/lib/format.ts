export function formatMs(value: number | null | undefined): string {
  if (!value) return "—";
  return new Date(value).toLocaleString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatRelative(value: number | null | undefined): string {
  if (!value) return "—";
  const diff = Date.now() - value;
  const minutes = Math.round(diff / 60_000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  if (days < 30) return `${days}d ago`;
  return new Date(value).toLocaleDateString("en-GB", { day: "2-digit", month: "short" });
}

export function initials(name: string): string {
  return (
    name
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase() ?? "")
      .join("") || "?"
  );
}

export function titleCase(value: string): string {
  return value
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function roleTone(role: string): "petrol" | "lime" | "muted" {
  if (role === "owner" || role === "admin") return "petrol";
  if (role === "editor") return "lime";
  return "muted";
}

export function statusTone(status: string): "petrol" | "lime" | "danger" | "muted" {
  if (status === "pending") return "lime";
  if (status === "accepted") return "petrol";
  if (status === "revoked" || status === "expired") return "danger";
  return "muted";
}

const ACTION_LABELS: Record<string, string> = {
  "workspace.created": "Workspace created",
  "workspace.updated": "Workspace updated",
  "workspace.member_role_changed": "Member role changed",
  "workspace.member_removed": "Member removed",
  "project.created": "Project created",
  "project.updated": "Project updated",
  "project.archived": "Project archived",
  "project.restored": "Project restored",
  "project.deleted": "Project deleted",
  "project.member_granted": "Project access granted",
  "project.member_removed": "Project access removed",
  "environment.created": "Environment created",
  "secret.created": "Secret created",
  "secret.updated": "Secret updated",
  "secret.deleted": "Secret deleted",
  "secret.revealed": "Secret revealed",
  "secret.downloaded": "Secrets downloaded",
  "secret.diffed": "Secrets compared",
  "secret.bulk_upserted": "Secrets pushed",
  "secret.copied": "Secrets copied",
  "secret.rolled_back": "Secret rolled back",
  "invite.created": "Invite created",
  "invite.updated": "Invite updated",
  "invite.resent": "Invite resent",
  "invite.revoked": "Invite revoked",
  "invite.accepted": "Invite accepted",
  "service_token.created": "Service token created",
  "service_token.revoked": "Service token revoked",
};

export function actionLabel(action: string): string {
  return ACTION_LABELS[action] ?? titleCase(action.replace(/\./g, " "));
}

export const AUDIT_ACTIONS = Object.keys(ACTION_LABELS).sort();

export function metadataSummary(metadata: Record<string, unknown>): string {
  const parts: string[] = [];
  for (const key of ["added", "updated", "removed", "unchanged", "count"]) {
    const value = metadata[key];
    if (typeof value === "number") parts.push(`${key} ${value}`);
  }
  for (const key of ["role", "mode", "format"]) {
    const value = metadata[key];
    if (typeof value === "string") parts.push(`${key} ${value}`);
  }
  const keys = ["addedKeys", "updatedKeys", "removedKeys", "keys"];
  for (const key of keys) {
    const value = metadata[key];
    if (Array.isArray(value) && value.length) {
      const shown = value.slice(0, 4).join(", ");
      parts.push(`${value.length} key${value.length === 1 ? "" : "s"}: ${shown}${value.length > 4 ? "…" : ""}`);
      break;
    }
  }
  return parts.join(" · ");
}

export function roleLabel(role: string): string {
  return titleCase(role);
}
