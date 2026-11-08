"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";

import { Dialog, DialogBody, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { apiPut } from "@/lib/api-client";
import type {
  Environment,
  ProjectMember,
  ProjectRole,
  WorkspaceMember,
} from "@/lib/types";

const PROJECT_ROLES: ProjectRole[] = ["viewer", "editor", "admin"];

export function GrantDialog({
  projectId,
  environments,
  workspaceMembers,
  projectMembers,
  target,
  open,
  onOpenChange,
}: {
  projectId: string;
  environments: Environment[];
  workspaceMembers: WorkspaceMember[];
  projectMembers: ProjectMember[];
  target: ProjectMember | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const options = target
    ? []
    : workspaceMembers.filter(
        (member) => !projectMembers.some((existing) => existing.userId === member.userId),
      );
  const [userId, setUserId] = useState(target?.userId ?? options[0]?.userId ?? "");
  const [role, setRole] = useState<ProjectRole>(target?.role ?? "viewer");
  const [allEnvironments, setAllEnvironments] = useState(!target?.environmentIds?.length);
  const [environmentIds, setEnvironmentIds] = useState<string[]>(target?.environmentIds ?? []);
  const [busy, setBusy] = useState(false);
  const queryClient = useQueryClient();

  function toggleEnvironment(id: string) {
    setEnvironmentIds((current) =>
      current.includes(id) ? current.filter((value) => value !== id) : [...current, id],
    );
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!userId) return;
    if (!allEnvironments && !environmentIds.length) {
      toast.error("Choose at least one environment or allow all.");
      return;
    }
    setBusy(true);
    try {
      await apiPut<ProjectMember>(
        `/api/v1/projects/${projectId}/members/${userId}`,
        {
          role,
          environmentIds: allEnvironments ? null : environmentIds,
        },
      );
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["project-members", projectId] }),
        queryClient.invalidateQueries({ queryKey: ["project", projectId] }),
        queryClient.invalidateQueries({ queryKey: ["projects"] }),
        queryClient.invalidateQueries({ queryKey: ["audit"] }),
      ]);
      toast.success(target ? "Access updated" : "Access granted");
      onOpenChange(false);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not save the grant.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{target ? `Edit access for ${target.name}` : "Grant project access"}</DialogTitle>
          <DialogDescription>
            Project roles only apply to people who are already workspace members.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={submit}>
          <DialogBody>
            {!target ? (
              options.length ? (
                <div className="sc-field">
                  <label className="sc-label" htmlFor="grant-member">
                    Workspace member
                  </label>
                  <select
                    id="grant-member"
                    className="sc-select"
                    value={userId}
                    onChange={(event) => setUserId(event.target.value)}
                  >
                    {options.map((member) => (
                      <option key={member.userId} value={member.userId}>
                        {member.name} · {member.email}
                      </option>
                    ))}
                  </select>
                </div>
              ) : (
                <p className="sc-help">
                  Everyone in this workspace already has a direct grant. Invite someone first.
                </p>
              )
            ) : (
              <p className="sc-person sc-person--sm">
                <strong>{target.name}</strong>
                <span>{target.email}</span>
              </p>
            )}
            <div className="sc-field">
              <label className="sc-label" htmlFor="grant-role">
                Project role
              </label>
              <select
                id="grant-role"
                className="sc-select"
                value={role}
                onChange={(event) => setRole(event.target.value as ProjectRole)}
              >
                {PROJECT_ROLES.map((projectRole) => (
                  <option key={projectRole} value={projectRole}>
                    {projectRole}
                  </option>
                ))}
              </select>
            </div>
            <div className="sc-field">
              <span className="sc-label">Environment access</span>
              <label className="sc-check-row">
                <input
                  type="checkbox"
                  checked={allEnvironments}
                  onChange={(event) => setAllEnvironments(event.target.checked)}
                />
                <span>All environments</span>
              </label>
              {!allEnvironments ? (
                <div className="sc-checkbox-list">
                  {environments.map((environment) => (
                    <label className="sc-check-row" key={environment.id}>
                      <input
                        type="checkbox"
                        checked={environmentIds.includes(environment.id)}
                        onChange={() => toggleEnvironment(environment.id)}
                      />
                      <span>{environment.name}</span>
                      <code className="sc-mono">{environment.slug}</code>
                    </label>
                  ))}
                </div>
              ) : null}
            </div>
          </DialogBody>
          <DialogFooter>
            <button type="button" className="sc-btn sc-btn--ghost" onClick={() => onOpenChange(false)}>
              Cancel
            </button>
            <button type="submit" className="sc-btn sc-btn--primary" disabled={busy || !userId}>
              {busy ? "Saving…" : target ? "Save access" : "Grant access"}
            </button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
