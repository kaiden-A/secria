"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { Dialog, DialogBody, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { apiPost } from "@/lib/api-client";
import type { Workspace } from "@/lib/types";

export function CreateWorkspaceDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [busy, setBusy] = useState(false);
  const queryClient = useQueryClient();
  const router = useRouter();

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!name.trim()) return;
    setBusy(true);
    try {
      const workspace = await apiPost<Workspace>("/api/v1/workspaces", {
        name: name.trim(),
        slug: slug.trim() || null,
      });
      await queryClient.invalidateQueries({ queryKey: ["workspaces"] });
      toast.success("Workspace created");
      onOpenChange(false);
      setName("");
      setSlug("");
      router.push(`/w/${workspace.slug}`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not create the workspace.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>New workspace</DialogTitle>
          <DialogDescription>
            A workspace is the top-level container for projects, environments, and members.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={submit}>
          <DialogBody>
            <div className="sc-field">
              <label className="sc-label" htmlFor="workspace-name">
                Name
              </label>
              <input
                id="workspace-name"
                className="sc-input"
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="Acme Engineering"
                required
              />
            </div>
            <div className="sc-field">
              <label className="sc-label" htmlFor="workspace-slug">
                Slug <span className="sc-optional">optional</span>
              </label>
              <input
                id="workspace-slug"
                className="sc-input"
                value={slug}
                onChange={(event) => setSlug(event.target.value)}
                placeholder="acme"
                pattern="[a-z0-9][a-z0-9-]*"
              />
              <p className="sc-help">Lowercase letters, numbers, and hyphens.</p>
            </div>
          </DialogBody>
          <DialogFooter>
            <button type="button" className="sc-btn sc-btn--ghost" onClick={() => onOpenChange(false)}>
              Cancel
            </button>
            <button type="submit" className="sc-btn sc-btn--primary" disabled={busy || !name.trim()}>
              {busy ? "Creating…" : "Create workspace"}
            </button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
