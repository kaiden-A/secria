"use client";

import { useQueryClient } from "@tanstack/react-query";
import { FileUp, Sparkles } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/bits";
import { Dialog, DialogBody, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { apiPost, apiPut } from "@/lib/api-client";
import { envPayload, parseEnvText, sha256Map } from "@/lib/env";
import type { BulkResult, DiffResult } from "@/lib/types";

export function ImportDialog({
  projectId,
  environmentId,
  open,
  onOpenChange,
}: {
  projectId: string;
  environmentId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [text, setText] = useState("");
  const [mode, setMode] = useState<"merge" | "replace">("merge");
  const [diff, setDiff] = useState<DiffResult | null>(null);
  const [previewing, setPreviewing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const base = `/api/v1/projects/${projectId}/environments/${environmentId}/secrets`;

  async function preview(): Promise<boolean> {
    const values = parseEnvText(text);
    if (!Object.keys(values).length) {
      setError("No secrets found in the import.");
      return false;
    }
    setError(null);
    setPreviewing(true);
    try {
      const hashes = sha256Map(values);
      const result = await apiPost<DiffResult>(`${base}/diff`, {
        secrets: Object.entries(hashes).map(([key, valueSha256]) => ({
          key,
          valueSha256,
        })),
      });
      setDiff(result);
      return true;
    } catch (cause) {
      const message =
        cause instanceof Error ? cause.message : "Could not compare the import.";
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
    const values = parseEnvText(text);
    if (!Object.keys(values).length) {
      setError("No secrets found in the import.");
      return;
    }
    setError(null);
    setBusy(true);
    try {
      const result = await apiPut<BulkResult>(base, {
        mode,
        secrets: envPayload(values),
      });
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["secrets", projectId, environmentId] }),
        queryClient.invalidateQueries({ queryKey: ["audit"] }),
      ]);
      toast.success(
        `Pushed ${result.added + result.updated} changes (${result.added} added, ${result.updated} updated).`,
      );
      onOpenChange(false);
    } catch (cause) {
      const message =
        cause instanceof Error ? cause.message : "Could not import the secrets.";
      setError(message);
      toast.error(message);
    } finally {
      setBusy(false);
    }
  }

  function loadFile(file: File | undefined) {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      setText(String(reader.result ?? ""));
      setDiff(null);
      setError(null);
    };
    reader.readAsText(file);
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sc-dialog--wide">
        <DialogHeader>
          <DialogTitle>Import .env</DialogTitle>
          <DialogDescription>
            Paste a .env file or choose one. Import compares keys and hashes first; values never leave
            the request body until you confirm.
          </DialogDescription>
        </DialogHeader>
        <DialogBody>
          <div className="sc-import-head">
            <label className="sc-btn sc-btn--ghost sc-btn--small sc-filebtn">
              <FileUp size={15} /> Choose file
              <input
                type="file"
                accept=".env,text/plain"
                onChange={(event) => loadFile(event.target.files?.[0])}
              />
            </label>
            <select
              className="sc-select sc-select--sm"
              value={mode}
              onChange={(event) => {
                setMode(event.target.value as "merge" | "replace");
                setDiff(null);
                setError(null);
              }}
              aria-label="Import mode"
            >
              <option value="merge">Merge</option>
              <option value="replace">Replace</option>
            </select>
          </div>
          <textarea
            className="sc-textarea sc-textarea--code"
            value={text}
            onChange={(event) => {
              setText(event.target.value);
              setDiff(null);
              setError(null);
            }}
            rows={10}
            placeholder={"DATABASE_URL=postgres://...\nAPI_KEY=...\n# comments are ignored"}
            spellCheck={false}
          />
          {mode === "replace" ? (
            <div className="sc-notice sc-notice--warn">
              <Sparkles size={16} />
              <span>Replace will soft-delete remote keys that are not in this file.</span>
            </div>
          ) : null}
          {diff ? (
            <div className="sc-diff">
              <div className="sc-diff-counts">
                <Badge tone="lime">+{diff.added.length} added</Badge>
                <Badge tone="petrol">~{diff.changed.length} changed</Badge>
                <Badge tone="danger">-{diff.removed.length} removed</Badge>
                <Badge tone="muted">={diff.unchanged.length} unchanged</Badge>
              </div>
              <div className="sc-diff-keys">
                {diff.added.length ? <p><span>Added</span> {diff.added.join(", ")}</p> : null}
                {diff.changed.length ? <p><span>Changed</span> {diff.changed.join(", ")}</p> : null}
                {diff.removed.length ? <p><span>Removed</span> {diff.removed.join(", ")}</p> : null}
              </div>
            </div>
          ) : null}
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
            disabled={previewing || busy || !text.trim()}
            aria-busy={previewing || busy}
          >
            {busy
              ? "Importing…"
              : previewing
                ? "Comparing…"
                : diff
                  ? "Import secrets"
                  : "Preview diff"}
          </button>
        </DialogFooter>
        <p className="sc-help sc-dialog-footnote">
          {diff
            ? "Review the changes above, then import. Nothing has been written yet."
            : "Preview the diff first; nothing is written until you confirm."}
        </p>
      </DialogContent>
    </Dialog>
  );
}
