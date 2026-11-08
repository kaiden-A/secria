"use client";

import { useQueryClient } from "@tanstack/react-query";
import { ShieldCheck, UserPlus, Users, X } from "lucide-react";
import { useParams } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { GrantDialog } from "@/components/GrantDialog";
import { ProjectShell, useProjectContext } from "@/components/ProjectShell";
import { Avatar, Badge, EmptyState, RoleBadge, Skeleton } from "@/components/ui/bits";
import { ConfirmDialog } from "@/components/ui/confirm";
import { PageHeader, SectionCard } from "@/components/ui/page";
import { apiDelete } from "@/lib/api-client";
import { formatRelative } from "@/lib/format";
import { useProjectMembers, useWorkspaceMembers } from "@/lib/queries";
import type { ProjectMember } from "@/lib/types";

function AccessPanel() {
  const { workspace, project } = useProjectContext();
  const members = useProjectMembers(project.id);
  const workspaceMembers = useWorkspaceMembers(workspace.id);
  const [grant, setGrant] = useState<{ target: ProjectMember | null } | null>(null);
  const [removeTarget, setRemoveTarget] = useState<ProjectMember | null>(null);
  const queryClient = useQueryClient();
  const canManage = project.role === "admin";

  const environmentNames = new Map(project.environments.map((env) => [env.id, env.name]));

  async function remove() {
    if (!removeTarget) return;
    await apiDelete(`/api/v1/projects/${project.id}/members/${removeTarget.userId}`);
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["project-members", project.id] }),
      queryClient.invalidateQueries({ queryKey: ["project", project.id] }),
      queryClient.invalidateQueries({ queryKey: ["projects"] }),
      queryClient.invalidateQueries({ queryKey: ["audit"] }),
    ]);
    toast.success("Project access removed");
    setRemoveTarget(null);
  }

  return (
    <>
      <PageHeader
        eyebrow="Project access"
        title="Who can see this project"
        description="Workspace owners and admins always have access. Direct grants can be limited to specific environments."
        actions={
          canManage ? (
            <button type="button" className="sc-btn sc-btn--primary" onClick={() => setGrant({ target: null })} disabled={workspaceMembers.isLoading}>
              <UserPlus size={16} /> Grant access
            </button>
          ) : undefined
        }
      />

      <SectionCard>
        {members.isLoading ? (
          <div className="sc-stack">
            {[0, 1, 2].map((index) => (
              <Skeleton key={index} className="sc-skeleton--row" />
            ))}
          </div>
        ) : members.data?.length ? (
          <div className="sc-table-wrap">
            <table className="sc-table">
              <thead>
                <tr>
                  <th>Person</th>
                  <th>Role</th>
                  <th>Source</th>
                  <th>Environments</th>
                  <th>Joined</th>
                  {canManage ? <th className="sc-cell-actions" /> : null}
                </tr>
              </thead>
              <tbody>
                {members.data.map((member) => (
                  <tr key={member.userId}>
                    <td>
                      <div className="sc-person">
                        <Avatar name={member.name} size={32} />
                        <div>
                          <strong>{member.name}</strong>
                          <span>{member.email}</span>
                        </div>
                      </div>
                    </td>
                    <td>
                      <RoleBadge role={member.role} />
                    </td>
                    <td>
                      <Badge tone={member.source === "workspace" ? "petrol" : "muted"}>
                        {member.source === "workspace" ? "Via workspace" : "Direct grant"}
                      </Badge>
                    </td>
                    <td className="sc-cell-muted">
                      {member.environmentIds === null
                        ? "All environments"
                        : member.environmentIds.length
                          ? member.environmentIds
                              .map((id) => environmentNames.get(id) ?? id)
                              .join(", ")
                          : "All environments"}
                    </td>
                    <td className="sc-cell-muted">{formatRelative(member.joinedAt)}</td>
                    {canManage ? (
                      <td className="sc-cell-actions">
                        {member.source === "project" ? (
                          <div className="sc-rowactions">
                            <button
                              type="button"
                              className="sc-iconbtn"
                              aria-label={`Edit access for ${member.name}`}
                              onClick={() => setGrant({ target: member })}
                            >
                              <ShieldCheck size={16} />
                            </button>
                            <button
                              type="button"
                              className="sc-iconbtn sc-iconbtn--danger"
                              aria-label={`Remove access for ${member.name}`}
                              onClick={() => setRemoveTarget(member)}
                            >
                              <X size={16} />
                            </button>
                          </div>
                        ) : null}
                      </td>
                    ) : null}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            icon={<Users size={24} />}
            title="No direct grants"
            body="Workspace admins already have access. Grant a member to let them see this project."
          />
        )}
      </SectionCard>

      {grant ? (
        <GrantDialog
          projectId={project.id}
          environments={project.environments}
          workspaceMembers={workspaceMembers.data ?? []}
          projectMembers={members.data ?? []}
          target={grant.target}
          open
          onOpenChange={(open) => !open && setGrant(null)}
        />
      ) : null}
      <ConfirmDialog
        open={Boolean(removeTarget)}
        onOpenChange={(open) => !open && setRemoveTarget(null)}
        title={`Remove ${removeTarget?.name ?? "member"}?`}
        description="They will lose direct access to this project. Workspace admins keep their implicit access."
        confirmLabel="Remove access"
        destructive
        onConfirm={remove}
      />
    </>
  );
}

export function AccessView() {
  const params = useParams<{ ws: string; project: string }>();
  return (
    <ProjectShell wsSlug={params.ws} projectSlug={params.project}>
      <AccessPanel />
    </ProjectShell>
  );
}
