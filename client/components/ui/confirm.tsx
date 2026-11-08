"use client";

import { useState } from "react";
import type { ReactNode } from "react";

import { Dialog, DialogBody, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";

export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel = "Confirm",
  destructive = false,
  onConfirm,
  children,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  confirmLabel?: string;
  destructive?: boolean;
  onConfirm: () => Promise<void> | void;
  children?: ReactNode;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handle() {
    setBusy(true);
    setError(null);
    try {
      await onConfirm();
      onOpenChange(false);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          {description ? <DialogDescription>{description}</DialogDescription> : null}
        </DialogHeader>
        {children ? <DialogBody>{children}</DialogBody> : null}
        {error ? (
          <p className="sc-error sc-error--pad" role="alert">
            {error}
          </p>
        ) : null}
        <DialogFooter>
          <button type="button" className="sc-btn sc-btn--ghost" onClick={() => onOpenChange(false)} disabled={busy}>
            Cancel
          </button>
          <button
            type="button"
            className={destructive ? "sc-btn sc-btn--danger" : "sc-btn sc-btn--primary"}
            onClick={() => void handle()}
            disabled={busy}
          >
            {busy ? "Working…" : confirmLabel}
          </button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
