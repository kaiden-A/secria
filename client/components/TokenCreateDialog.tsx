"use client";

import { Copy, KeyRound, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Dialog, DialogBody, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { apiPost } from "@/lib/api-client";
import { copyText } from "@/lib/env";

export function TokenCreatedDialog({
  open,
  onOpenChange,
  token,
  name,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  token: string;
  name: string;
}) {
  async function copy() {
    try {
      await copyText(token);
      toast.success("Token copied");
    } catch {
      toast.error("Could not copy the token.");
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Service token created</DialogTitle>
          <DialogDescription>
            Copy <strong>{name}</strong> now. Secria stores only a hash and cannot show it again.
          </DialogDescription>
        </DialogHeader>
        <DialogBody>
          <div className="sc-notice sc-notice--lime">
            <ShieldCheck size={17} />
            <span>Shown once. Treat it like a password.</span>
          </div>
          <div className="sc-copyrow">
            <input className="sc-input sc-mono" value={token} readOnly aria-label="Service token" />
            <button type="button" className="sc-btn sc-btn--ghost" onClick={() => void copy()}>
              <Copy size={15} /> Copy
            </button>
          </div>
        </DialogBody>
        <DialogFooter>
          <button type="button" className="sc-btn sc-btn--primary" onClick={() => onOpenChange(false)}>
            Done
          </button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function TokenCreateDialog({
  open,
  onOpenChange,
  projectId,
  environmentId,
  onCreated,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectId: string;
  environmentId: string;
  onCreated: (token: string, name: string) => void;
}) {
  const [name, setName] = useState("");
  const [access, setAccess] = useState<"read" | "read_write">("read");
  const [days, setDays] = useState("");
  const [busy, setBusy] = useState(false);
  const [created, setCreated] = useState<{ token: string; name: string } | null>(null);

  function close(next: boolean) {
    onOpenChange(next);
    if (!next) {
      setName("");
      setAccess("read");
      setDays("");
      setCreated(null);
    }
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!name.trim()) return;
    setBusy(true);
    try {
      const parsedDays = days.trim() ? Number(days) : null;
      const result = await apiPost<{ token: string; name: string }>(
        `/api/v1/projects/${projectId}/environments/${environmentId}/service-tokens`,
        {
          name: name.trim(),
          access,
          expiresAt: parsedDays
            ? Date.now() + Math.max(1, parsedDays) * 86_400_000
            : null,
        },
      );
      setCreated({ token: result.token, name: result.name });
      onCreated(result.token, result.name);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not create the token.");
    } finally {
      setBusy(false);
    }
  }

  if (created) {
    return (
      <TokenCreatedDialog
        open={open}
        onOpenChange={close}
        token={created.token}
        name={created.name}
      />
    );
  }

  return (
    <Dialog open={open} onOpenChange={close}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>New service token</DialogTitle>
          <DialogDescription>
            Scoped to this project and environment. Use it in CI through <code>SECRIA_TOKEN</code>.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={submit}>
          <DialogBody>
            <div className="sc-field">
              <label className="sc-label" htmlFor="token-name">
                Name
              </label>
              <input
                id="token-name"
                className="sc-input"
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="ci-github"
                required
              />
            </div>
            <div className="sc-grid-2">
              <div className="sc-field">
                <label className="sc-label" htmlFor="token-access">
                  Access
                </label>
                <select
                  id="token-access"
                  className="sc-select"
                  value={access}
                  onChange={(event) => setAccess(event.target.value as "read" | "read_write")}
                >
                  <option value="read">Read only</option>
                  <option value="read_write">Read and write</option>
                </select>
              </div>
              <div className="sc-field">
                <label className="sc-label" htmlFor="token-days">
                  Expires in days <span className="sc-optional">optional</span>
                </label>
                <input
                  id="token-days"
                  className="sc-input"
                  type="number"
                  min={1}
                  value={days}
                  onChange={(event) => setDays(event.target.value)}
                  placeholder="Never"
                />
              </div>
            </div>
            <p className="sc-help">
              <KeyRound size={13} /> Tokens are hashed at rest and shown once.
            </p>
          </DialogBody>
          <DialogFooter>
            <button type="button" className="sc-btn sc-btn--ghost" onClick={() => close(false)}>
              Cancel
            </button>
            <button type="submit" className="sc-btn sc-btn--primary" disabled={busy || !name.trim()}>
              {busy ? "Creating…" : "Create token"}
            </button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
