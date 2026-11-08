"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";

import { InviteLinkDialog } from "@/components/InviteLinkDialog";
import { Dialog, DialogBody, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { apiPost } from "@/lib/api-client";
import type { InviteCreateResult, Project, ProjectRole, WorkspaceRole } from "@/lib/types";

const PROJECT_ROLES: ProjectRole[] = ["viewer", "editor", "admin"];

export function InviteDialog({
  workspaceId,
  projects,
  canInviteOwner,
  open,
  onOpenChange,
}: {
  workspaceId: string;
  projects: Project[];
  canInviteOwner: boolean;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<WorkspaceRole>("member");
  const [grants, setGrants] = useState<Record<string, ProjectRole | "none">>({});
  const [busy, setBusy] = useState(false);
  const [created, setCreated] = useState<InviteCreateResult | null>(null);
  const queryClient = useQueryClient();

  function reset() {
    setEmail("");
    setRole("member");
    setGrants({});
    setCreated(null);
  }

  function close(next: boolean) {
    onOpenChange(next);
    if (!next) reset();
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      const result = await apiPost<InviteCreateResult>(
        `/api/v1/workspaces/${workspaceId}/invites`,
        {
          email: email.trim(),
          role,
          grants: Object.entries(grants)
            .filter(([, projectRole]) => projectRole !== "none")
            .map(([projectId, projectRole]) => ({ projectId, role: projectRole })),
        },
      );
      await queryClient.invalidateQueries({ queryKey: ["invites", workspaceId] });
      setCreated(result);
      toast.success("Invite created");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not create the invite.");
    } finally {
      setBusy(false);
    }
  }

  if (created) {
    return (
      <InviteLinkDialog
        open={open}
        onOpenChange={close}
        inviteUrl={created.inviteUrl}
        emailSent={created.emailSent}
      />
    );
  }

  return (
    <Dialog open={open} onOpenChange={close}>
      <DialogContent className="sc-dialog--wide">
        <DialogHeader>
          <DialogTitle>Invite someone</DialogTitle>
          <DialogDescription>
            They must sign in with the same verified email. Project grants are optional.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={submit}>
          <DialogBody>
            <div className="sc-grid-2">
              <div className="sc-field">
                <label className="sc-label" htmlFor="invite-email">
                  Email
                </label>
                <input
                  id="invite-email"
                  className="sc-input"
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="teammate@company.com"
                  required
                />
              </div>
              <div className="sc-field">
                <label className="sc-label" htmlFor="invite-role">
                  Workspace role
                </label>
                <select
                  id="invite-role"
                  className="sc-select"
                  value={role}
                  onChange={(event) => setRole(event.target.value as WorkspaceRole)}
                >
                  <option value="member">Member</option>
                  <option value="admin">Admin</option>
                  {canInviteOwner ? <option value="owner">Owner</option> : null}
                </select>
              </div>
            </div>

            <div className="sc-field">
              <span className="sc-label">Project access</span>
              {projects.length ? (
                <div className="sc-grant-list">
                  {projects.map((project) => (
                    <div className="sc-grant-row" key={project.id}>
                      <div>
                        <strong>{project.name}</strong>
                        <span className="sc-mono">{project.slug}</span>
                      </div>
                      <select
                        className="sc-select sc-select--sm"
                        value={grants[project.id] ?? "none"}
                        onChange={(event) =>
                          setGrants((current) => ({
                            ...current,
                            [project.id]: event.target.value as ProjectRole | "none",
                          }))
                        }
                        aria-label={`Role for ${project.name}`}
                      >
                        <option value="none">No access</option>
                        {PROJECT_ROLES.map((projectRole) => (
                          <option key={projectRole} value={projectRole}>
                            {projectRole}
                          </option>
                        ))}
                      </select>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="sc-help">No active projects yet.</p>
              )}
            </div>
          </DialogBody>
          <DialogFooter>
            <button type="button" className="sc-btn sc-btn--ghost" onClick={() => close(false)}>
              Cancel
            </button>
            <button type="submit" className="sc-btn sc-btn--primary" disabled={busy || !email.trim()}>
              {busy ? "Creating…" : "Create invite"}
            </button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
