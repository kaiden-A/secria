"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";

import { Dialog, DialogBody, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { apiPut } from "@/lib/api-client";
import type { BulkResult, Secret } from "@/lib/types";

export function SecretDialog({
  projectId,
  environmentId,
  open,
  onOpenChange,
  initial,
}: {
  projectId: string;
  environmentId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initial?: Secret | null;
}) {
  const editing = Boolean(initial);
  const [key, setKey] = useState(initial?.key ?? "");
  const [value, setValue] = useState("");
  const [comment, setComment] = useState(initial?.comment ?? "");
  const [busy, setBusy] = useState(false);
  const queryClient = useQueryClient();

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!key.trim() || !value) return;
    setBusy(true);
    try {
      await apiPut<BulkResult>(
        `/api/v1/projects/${projectId}/environments/${environmentId}/secrets`,
        {
          mode: "merge",
          secrets: [
            {
              key: key.trim(),
              value,
              comment: comment.trim(),
            },
          ],
        },
      );
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["secrets", projectId, environmentId] }),
        queryClient.invalidateQueries({ queryKey: ["audit"] }),
      ]);
      toast.success(editing ? "Secret updated" : "Secret created");
      onOpenChange(false);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not save the secret.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{editing ? `Update ${initial?.key}` : "New secret"}</DialogTitle>
          <DialogDescription>
            Values are encrypted before they reach the database. Updates create a new version.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={submit}>
          <DialogBody>
            <div className="sc-field">
              <label className="sc-label" htmlFor="secret-key">
                Key
              </label>
              <input
                id="secret-key"
                className="sc-input sc-mono"
                value={key}
                onChange={(event) => setKey(event.target.value.toUpperCase())}
                placeholder="DATABASE_URL"
                pattern="[A-Z_][A-Z0-9_]*"
                readOnly={editing}
                required
              />
              <p className="sc-help">Uppercase letters, numbers, and underscores.</p>
            </div>
            <div className="sc-field">
              <label className="sc-label" htmlFor="secret-value">
                {editing ? "New value" : "Value"}
              </label>
              <textarea
                id="secret-value"
                className="sc-textarea sc-mono"
                value={value}
                onChange={(event) => setValue(event.target.value)}
                placeholder={editing ? "Enter the new value" : "The secret value"}
                rows={4}
                spellCheck={false}
                autoComplete="off"
                required
              />
            </div>
            <div className="sc-field">
              <label className="sc-label" htmlFor="secret-comment">
                Comment <span className="sc-optional">optional</span>
              </label>
              <input
                id="secret-comment"
                className="sc-input"
                value={comment}
                onChange={(event) => setComment(event.target.value)}
                placeholder="What changed and why?"
                maxLength={500}
              />
            </div>
          </DialogBody>
          <DialogFooter>
            <button type="button" className="sc-btn sc-btn--ghost" onClick={() => onOpenChange(false)}>
              Cancel
            </button>
            <button type="submit" className="sc-btn sc-btn--primary" disabled={busy || !key.trim() || !value}>
              {busy ? "Saving…" : editing ? "Save new version" : "Create secret"}
            </button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
