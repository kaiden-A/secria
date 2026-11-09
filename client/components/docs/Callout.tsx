import type { ReactNode } from "react";

import { Check, Shield, Terminal } from "@/components/Icons";

type Tone = "note" | "tip" | "warn" | "danger";

const ICONS = {
  note: Terminal,
  tip: Check,
  warn: Shield,
  danger: Shield,
} as const;

export function Callout({
  tone = "note",
  title,
  children,
}: {
  tone?: Tone;
  title?: string;
  children: ReactNode;
}) {
  const Icon = ICONS[tone];
  return (
    <aside className={`sc-docs-callout sc-docs-callout--${tone}`}>
      <Icon size={18} />
      <div className="sc-docs-callout-body">
        {title ? <strong>{title}</strong> : null}
        {children}
      </div>
    </aside>
  );
}
