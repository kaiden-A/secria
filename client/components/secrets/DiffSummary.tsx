"use client";

import { Badge } from "@/components/ui/bits";
import type { DiffResult } from "@/lib/types";

function keyList(keys: string[], limit = 24): string {
  if (keys.length <= limit) return keys.join(", ");
  return `${keys.slice(0, limit).join(", ")} +${keys.length - limit} more`;
}

export function DiffSummary({
  diff,
  mode,
  targetName,
}: {
  diff: DiffResult;
  mode: "merge" | "replace";
  targetName: string;
}) {
  const changes =
    diff.added.length + diff.changed.length + (mode === "replace" ? diff.removed.length : 0);
  const removedLabel = mode === "replace" ? "Will be removed" : `Only in ${targetName}`;

  return (
    <div className="sc-diff">
      <div className="sc-diff-counts">
        <Badge tone="lime">+{diff.added.length} added</Badge>
        <Badge tone="petrol">~{diff.changed.length} changed</Badge>
        <Badge tone={mode === "replace" ? "danger" : "muted"}>
          {mode === "replace"
            ? `-${diff.removed.length} removed`
            : `${diff.removed.length} only in destination`}
        </Badge>
        <Badge tone="muted">={diff.unchanged.length} unchanged</Badge>
      </div>
      <div className="sc-diff-keys">
        {diff.added.length ? (
          <p>
            <span>Added</span>
            {keyList(diff.added)}
          </p>
        ) : null}
        {diff.changed.length ? (
          <p>
            <span>Changed</span>
            {keyList(diff.changed)}
          </p>
        ) : null}
        {diff.removed.length ? (
          <p>
            <span>{removedLabel}</span>
            {keyList(diff.removed)}
          </p>
        ) : null}
        {!diff.added.length && !diff.changed.length && !diff.removed.length ? (
          <p className="sc-diff-empty">No changes to apply with this mode.</p>
        ) : null}
      </div>
      {changes > 0 ? (
        <p className="sc-diff-note">
          Unchanged values keep their current version. Nothing is written until you confirm.
        </p>
      ) : null}
    </div>
  );
}
