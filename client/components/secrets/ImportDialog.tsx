"use client";

import { useQueryClient } from "@tanstack/react-query";
import { FileUp, TriangleAlert } from "lucide-react";
import { useMemo, useState } from "react";
import type { DragEvent } from "react";
import { toast } from "sonner";

import { DiffSummary } from "@/components/secrets/DiffSummary";
import { Dialog, DialogBody, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { apiPost, apiPut } from "@/lib/api-client";
import { envPayload, parseEnvText, sha256Map } from "@/lib/env";
import type { BulkResult, DiffResult, Environment } from "@/lib/types";

export function ImportDialog({
  projectId,
  environmentId,
  environments,
  open,
  onOpenChange,
  onImported,
}: {
  projectId: string;
  environmentId: string;
  environments: Environment[];
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onImported?: (environment: Environment) => void;
}) {
  const [targetId, setTargetId] = useState(environmentId);
  const [text, setText] = useState("");
  const [fileName, setFileName] = useState("");
  const [dragging, setDragging] = useState(false);
  const [mode, setMode] = useState<"merge" | "replace">("merge");
  const [diff, setDiff] = useState<DiffResult | null>(null);
  const [previewing, setPreviewing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const target = environments.find((item) => item.id === targetId) ?? environments[0];
  const keyCount = useMemo(() => {
    if (!text.trim()) return 0;
    return Object.keys(parseEnvText(text)).length;
  }, [text]);

  if (!target) return null;

  const base = `/api/v1/projects/${projectId}/environments/${target.id}/secrets`;

  function resetPreview() {
    setDiff(null);
    setError(null);
  }

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
        queryClient.invalidateQueries({ queryKey: ["secrets", projectId, target.id] }),
        queryClient.invalidateQueries({ queryKey: ["audit"] }),
      ]);
      toast.success(
        `Imported ${result.added + result.updated} changes into ${target.name} (${result.added} added, ${result.updated} updated).`,
      );
      onOpenChange(false);
      onImported?.(target);
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
      setFileName(file.name);
      resetPreview();
    };
    reader.readAsText(file);
  }

  function onDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);
    if (previewing || busy) return;
    loadFile(event.dataTransfer.files?.[0]);
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sc-dialog--wide">
        <DialogHeader>
          <DialogTitle>Import .env</DialogTitle>
          <DialogDescription>
            Choose where the secrets land, then preview the diff. Values are only written when you
            confirm.
          </DialogDescription>
        </DialogHeader>
        <DialogBody>
          <div className="sc-grid-2">
            <label className="sc-field">
              <span className="sc-label">Import into</span>
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
            <div className="sc-field">
              <span className="sc-label">Mode</span>
              <div className="sc-segmented" role="group" aria-label="Import mode">
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
                  ? "Add and update keys; keep keys that only exist in the destination."
                  : "Mirror the file; soft-delete destination keys missing from it."}
              </p>
            </div>
          </div>

          <div
            className={`sc-import-drop${dragging ? " is-dragging" : ""}`}
            onDragOver={(event) => {
              event.preventDefault();
              if (!previewing && !busy) setDragging(true);
            }}
            onDragLeave={(event) => {
              if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
                setDragging(false);
              }
            }}
            onDrop={onDrop}
          >
            <div className="sc-import-drophead">
              <span className="sc-import-dropicon">
                <FileUp size={18} />
              </span>
              <div>
                <strong>{fileName || "Drop a .env file here"}</strong>
                <p>
                  {keyCount
                    ? `${keyCount} key${keyCount === 1 ? "" : "s"} detected`
                    : "or paste the contents below"}
                </p>
              </div>
              <label className="sc-btn sc-btn--ghost sc-btn--small sc-filebtn">
                Choose file
                <input
                  type="file"
                  accept=".env,text/plain"
                  disabled={previewing || busy}
                  onChange={(event) => {
                    loadFile(event.target.files?.[0]);
                    event.target.value = "";
                  }}
                />
              </label>
            </div>
            <textarea
              className="sc-textarea sc-textarea--code"
              value={text}
              disabled={previewing || busy}
              onChange={(event) => {
                setText(event.target.value);
                setFileName("");
                resetPreview();
              }}
              rows={9}
              placeholder={"DATABASE_URL=postgres://...\nAPI_KEY=...\n# comments are ignored"}
              spellCheck={false}
              aria-label=".env contents"
            />
          </div>

          {mode === "replace" ? (
            <div className="sc-notice sc-notice--warn">
              <TriangleAlert size={16} />
              <span>Replace will soft-delete destination keys that are not in this file.</span>
            </div>
          ) : null}
          {diff ? <DiffSummary diff={diff} mode={mode} targetName={target.name} /> : null}
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
                  ? `Import into ${target.name}`
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
