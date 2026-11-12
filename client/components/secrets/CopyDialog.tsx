"use client";

import { useQueryClient } from "@tanstack/react-query";
import { ArrowRightLeft, TriangleAlert } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { DiffSummary } from "@/components/secrets/DiffSummary";
import { Dialog, DialogBody, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { apiPost } from "@/lib/api-client";
import type { BulkResult, DiffResult, Environment } from "@/lib/types";

export function CopyDialog({
  projectId,
  environment,
  environments,
  open,
  onOpenChange,
  onCopied,
}: {
  projectId: string;
  environment: Environment;
  environments: Environment[];
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCopied?: (environment: Environment) => void;
}) {
  const currentIndex = environments.findIndex((item) => item.id === environment.id);
  const preferredTarget =
    environments[
      currentIndex === environments.length - 1 ? 0 : environments.length - 1
    ] ?? environment;
  const [sourceId, setSourceId] = useState(environment.id);
  const [targetId, setTargetId] = useState(preferredTarget.id);
  const [mode, setMode] = useState<"merge" | "replace">("merge");
  const [diff, setDiff] = useState<DiffResult | null>(null);
  const [previewing, setPreviewing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const source = environments.find((item) => item.id === sourceId) ?? environment;
  const target = environments.find((item) => item.id === targetId) ?? preferredTarget;
  const sameEnvironment = source.id === target.id;
  const changes = diff
    ? diff.added.length +
      diff.changed.length +
      (mode === "replace" ? diff.removed.length : 0)
    : 0;

  function resetPreview() {
    setDiff(null);
    setError(null);
  }

  async function preview(): Promise<boolean> {
    if (sameEnvironment) {
      setError("Choose two different environments.");
      return false;
    }
    setError(null);
    setPreviewing(true);
    try {
      const result = await apiPost<DiffResult>(
        `/api/v1/projects/${projectId}/environments/${target.id}/secrets/copy/preview`,
        { sourceEnvironmentId: source.id },
      );
      setDiff(result);
      return true;
    } catch (cause) {
      const message =
        cause instanceof Error ? cause.message : "Could not compare the environments.";
      setError(message);
      toast.error(message);
      return false;
    } finally {
      setPreviewing(false);
    }
  }

  async function submit() {
    if (!diff) {
      await preview();
      return;
    }
    if (sameEnvironment || changes === 0) return;
    setError(null);
    setBusy(true);
    try {
      const result = await apiPost<BulkResult>(
        `/api/v1/projects/${projectId}/environments/${target.id}/secrets/copy`,
        { sourceEnvironmentId: source.id, mode },
      );
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["secrets", projectId, target.id] }),
        queryClient.invalidateQueries({ queryKey: ["audit"] }),
      ]);
      const review = diff.changed.slice(0, 6).join(", ");
      const more = diff.changed.length > 6 ? ` +${diff.changed.length - 6} more` : "";
      toast.success(
        `Copied ${source.name} into ${target.name} (${result.added} added, ${result.updated} updated${result.removed ? `, ${result.removed} removed` : ""}).`,
        {
          description: diff.changed.length
            ? `Review changed keys: ${review}${more}`
            : "All source keys are now in the destination.",
        },
      );
      onOpenChange(false);
      onCopied?.(target);
    } catch (cause) {
      const message =
        cause instanceof Error ? cause.message : "Could not copy the secrets.";
      setError(message);
      toast.error(message);
    } finally {
      setBusy(false);
    }
  }

  function swap() {
    setSourceId(target.id);
    setTargetId(source.id);
    resetPreview();
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sc-dialog--wide">
        <DialogHeader>
          <DialogTitle>Copy secrets</DialogTitle>
          <DialogDescription>
            Copy one environment into another. Values are re-encrypted for the destination; the
            source environment is left unchanged.
          </DialogDescription>
        </DialogHeader>
        <DialogBody>
          <div className="sc-copy-route">
            <label className="sc-field">
              <span className="sc-label">From</span>
              <select
                className="sc-select"
                value={source.id}
                disabled={previewing || busy}
                onChange={(event) => {
                  setSourceId(event.target.value);
                  resetPreview();
                }}
              >
                {environments.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name}
                  </option>
                ))}
              </select>
            </label>
            <button
              type="button"
              className="sc-copy-swap"
              aria-label="Swap source and destination"
              disabled={previewing || busy}
              onClick={swap}
            >
              <ArrowRightLeft size={16} />
            </button>
            <label className="sc-field">
              <span className="sc-label">To</span>
              <select
                className="sc-select"
                value={target.id}
                disabled={previewing || busy}
                onChange={(event) => {
                  setTargetId(event.target.value);
                  resetPreview();
                }}
              >
                {environments.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="sc-field">
            <span className="sc-label">Mode</span>
            <div className="sc-segmented" role="group" aria-label="Copy mode">
              <button
                type="button"
                className={mode === "merge" ? "is-active" : ""}
                aria-pressed={mode === "merge"}
                disabled={previewing || busy}
                onClick={() => setMode("merge")}
              >
                Merge
              </button>
              <button
                type="button"
                className={mode === "replace" ? "is-active" : ""}
                aria-pressed={mode === "replace"}
                disabled={previewing || busy}
                onClick={() => setMode("replace")}
              >
                Replace
              </button>
            </div>
            <p className="sc-help">
              {mode === "merge"
                ? "Add missing keys and update changed ones; keep keys that only exist in the destination."
                : "Mirror the source; soft-delete destination keys missing from it."}
            </p>
          </div>

          {sameEnvironment ? (
            <div className="sc-notice sc-notice--warn">
              <TriangleAlert size={16} />
              <span>Choose two different environments before comparing.</span>
            </div>
          ) : null}
          {mode === "replace" && !sameEnvironment ? (
            <div className="sc-notice sc-notice--warn">
              <TriangleAlert size={16} />
              <span>Replace will soft-delete {target.name} keys that are not in {source.name}.</span>
            </div>
          ) : null}

          {diff ? (
            <DiffSummary diff={diff} mode={mode} targetName={target.name} />
          ) : (
            <div className="sc-copy-placeholder">
              <ArrowRightLeft size={18} />
              <p>
                Compare {source.name} with {target.name} first. Nothing is copied until you confirm.
              </p>
            </div>
          )}
          {error ? (
            <p className="sc-error" role="alert">
              {error}
            </p>
          ) : null}
        </DialogBody>
        <DialogFooter>
          <button type="button" className="sc-btn sc-btn--ghost" onClick={() => onOpenChange(false)}>
            Cancel
          </button>
          <button
            type="button"
            className="sc-btn sc-btn--primary"
            onClick={() => void submit()}
            disabled={previewing || busy || sameEnvironment || (Boolean(diff) && changes === 0)}
            aria-busy={previewing || busy}
          >
            {busy
              ? "Copying…"
              : previewing
                ? "Comparing…"
                : diff
                  ? changes === 0
                    ? "Nothing to copy"
                    : `Copy into ${target.name}`
                  : "Preview diff"}
          </button>
        </DialogFooter>
        <p className="sc-help sc-dialog-footnote">
          {diff
            ? "Review the changes above, then copy. Nothing has been written yet."
            : "Preview the diff first; nothing is written until you confirm."}
        </p>
      </DialogContent>
    </Dialog>
  );
}
