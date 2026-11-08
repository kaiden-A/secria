"use client";

import { LoaderCircle } from "lucide-react";
import type { CSSProperties, ReactNode } from "react";

import { initials, roleLabel, roleTone, statusTone, titleCase } from "@/lib/format";
import { cn } from "@/lib/utils";

const AVATAR_COLORS = ["#0a3a46", "#146071", "#4f7100", "#8a76d9", "#c8452f", "#5c9ae0"];

function avatarColor(name: string): string {
  const total = [...name].reduce((sum, char) => sum + char.charCodeAt(0), 0);
  return AVATAR_COLORS[total % AVATAR_COLORS.length];
}

export function Avatar({
  name,
  size = 32,
  className,
}: {
  name: string;
  size?: number;
  className?: string;
}) {
  return (
    <span
      className={cn("sc-avatar", className)}
      style={
        {
          width: size,
          height: size,
          background: avatarColor(name),
          fontSize: Math.max(9, Math.round(size * 0.36)),
        } as CSSProperties
      }
      aria-hidden="true"
    >
      {initials(name)}
    </span>
  );
}

export function Badge({
  children,
  tone = "muted",
  className,
}: {
  children: ReactNode;
  tone?: "petrol" | "lime" | "muted" | "danger";
  className?: string;
}) {
  return <span className={cn("sc-badge", `sc-badge--${tone}`, className)}>{children}</span>;
}

export function RoleBadge({ role }: { role: string }) {
  return <Badge tone={roleTone(role)}>{roleLabel(role)}</Badge>;
}

export function StatusBadge({ status }: { status: string }) {
  return <Badge tone={statusTone(status)}>{titleCase(status)}</Badge>;
}

export function EmptyState({
  icon,
  title,
  body,
  action,
  compact = false,
}: {
  icon: ReactNode;
  title: string;
  body?: string;
  action?: ReactNode;
  compact?: boolean;
}) {
  return (
    <div className={cn("sc-empty", compact && "sc-empty--compact")}>
      <span className="sc-empty-icon">{icon}</span>
      <h3>{title}</h3>
      {body ? <p>{body}</p> : null}
      {action ? <div className="sc-empty-action">{action}</div> : null}
    </div>
  );
}

export function Skeleton({ className, style }: { className?: string; style?: CSSProperties }) {
  return <span className={cn("sc-skeleton", className)} style={style} aria-hidden="true" />;
}

export function Spinner({ label = "Loading" }: { label?: string }) {
  return (
    <span className="sc-spinner" role="status" aria-label={label}>
      <LoaderCircle size={18} className="sc-spin" />
    </span>
  );
}
