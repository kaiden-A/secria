"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { Dialog, DialogBody, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { apiPost } from "@/lib/api-client";
import type { ProjectDetail } from "@/lib/types";

export function CreateProjectDialog({
  workspaceId,
  workspaceSlug,
  open,
  onOpenChange,
}: {
  workspaceId: string;
  workspaceSlug: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);
  const queryClient = useQueryClient();
  const router = useRouter();

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!name.trim()) return;
    setBusy(true);
    try {
      const project = await apiPost<ProjectDetail>(
        `/api/v1/workspaces/${workspaceId}/projects`,
        {
          name: name.trim(),
          slug: slug.trim() || null,
          description: description.trim(),
        },
      );
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["projects", workspaceId] }),
        queryClient.invalidateQueries({ queryKey: ["workspaces"] }),
      ]);
      toast.success("Project created");
      onOpenChange(false);
      setName("");
      setSlug("");
      setDescription("");
      router.push(`/w/${workspaceSlug}/p/${project.slug}`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not create the project.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>New project</DialogTitle>
          <DialogDescription>
            Every project gets its own key, members, and dev/staging/prod environments.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={submit}>
          <DialogBody>
            <div className="sc-field">
              <label className="sc-label" htmlFor="project-name">
                Name
              </label>
              <input
                id="project-name"
                className="sc-input"
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="Payments API"
                required
              />
            </div>
            <div className="sc-grid-2">
              <div className="sc-field">
                <label className="sc-label" htmlFor="project-slug">
                  Slug <span className="sc-optional">optional</span>
                </label>
                <input
                  id="project-slug"
                  className="sc-input"
                  value={slug}
                  onChange={(event) => setSlug(event.target.value)}
                  placeholder="payments-api"
                  pattern="[a-z0-9][a-z0-9-]*"
                />
              </div>
              <div className="sc-field">
                <label className="sc-label" htmlFor="project-description">
                  Description
                </label>
                <input
                  id="project-description"
                  className="sc-input"
                  value={description}
                  onChange={(event) => setDescription(event.target.value)}
                  placeholder="What lives here?"
                />
              </div>
            </div>
            <p className="sc-help">
              Defaults: <code>dev</code>, <code>staging</code>, <code>prod</code>.
            </p>
          </DialogBody>
          <DialogFooter>
            <button type="button" className="sc-btn sc-btn--ghost" onClick={() => onOpenChange(false)}>
              Cancel
            </button>
            <button type="submit" className="sc-btn sc-btn--primary" disabled={busy || !name.trim()}>
              {busy ? "Creating…" : "Create project"}
            </button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
