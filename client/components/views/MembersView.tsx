"use client";

import { useQueryClient } from "@tanstack/react-query";
import { MailPlus, RotateCw, UserPlus, Users, X } from "lucide-react";
import { useParams } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { InviteDialog } from "@/components/InviteDialog";
import { InviteLinkDialog } from "@/components/InviteLinkDialog";
import { Avatar, Badge, EmptyState, RoleBadge, Skeleton, StatusBadge } from "@/components/ui/bits";
import { ConfirmDialog } from "@/components/ui/confirm";
import { Page, PageHeader, SectionCard } from "@/components/ui/page";
import { apiDelete, apiPatch, apiPost } from "@/lib/api-client";
import { formatMs, formatRelative, roleLabel } from "@/lib/format";
import {
  useInvites,
  useMe,
  useProjects,
  useWorkspace,
  useWorkspaceMembers,
} from "@/lib/queries";
import type { Invite, InviteResendResult, WorkspaceMember, WorkspaceRole } from "@/lib/types";

const WORKSPACE_ROLES: WorkspaceRole[] = ["owner", "admin", "member"];

export function MembersView() {
  const params = useParams<{ ws: string }>();
  const wsSlug = params.ws;
  const workspace = useWorkspace(wsSlug);
  const me = useMe();
  const members = useWorkspaceMembers(workspace.workspace?.id);
  const role = workspace.workspace?.role;
  const canManage = role === "owner" || role === "admin";
  const isOwner = role === "owner";
  const invites = useInvites(workspace.workspace?.id, canManage);
  const projects = useProjects(workspace.workspace?.id);
  const queryClient = useQueryClient();

  const [inviteOpen, setInviteOpen] = useState(false);
  const [linkUrl, setLinkUrl] = useState("");
  const [linkEmailSent, setLinkEmailSent] = useState(false);
  const [linkOpen, setLinkOpen] = useState(false);
  const [removeTarget, setRemoveTarget] = useState<WorkspaceMember | null>(null);
  const [revokeTarget, setRevokeTarget] = useState<Invite | null>(null);
  const [busyMember, setBusyMember] = useState<string | null>(null);
  const [busyInvite, setBusyInvite] = useState<string | null>(null);

  async function invalidate() {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["members", workspace.workspace?.id] }),
      queryClient.invalidateQueries({ queryKey: ["invites", workspace.workspace?.id] }),
      queryClient.invalidateQueries({ queryKey: ["workspaces"] }),
      queryClient.invalidateQueries({ queryKey: ["projects"] }),
      queryClient.invalidateQueries({ queryKey: ["project-members"] }),
      queryClient.invalidateQueries({ queryKey: ["audit", workspace.workspace?.id] }),
    ]);
  }

  async function changeRole(member: WorkspaceMember, nextRole: WorkspaceRole) {
    setBusyMember(member.userId);
    try {
      await apiPatch(
        `/api/v1/workspaces/${workspace.workspace?.id}/members/${member.userId}`,
        { role: nextRole },
      );
      await invalidate();
      toast.success("Role updated");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not update the role.");
    } finally {
      setBusyMember(null);
    }
  }

  async function removeMember() {
    if (!removeTarget) return;
    await apiDelete(
      `/api/v1/workspaces/${workspace.workspace?.id}/members/${removeTarget.userId}`,
    );
    await invalidate();
    toast.success("Member removed");
    setRemoveTarget(null);
  }

  async function resend(invite: Invite) {
    setBusyInvite(invite.id);
    try {
      const result = await apiPost<InviteResendResult>(
        `/api/v1/workspaces/${workspace.workspace?.id}/invites/${invite.id}/resend`,
      );
      setLinkUrl(result.inviteUrl);
      setLinkEmailSent(result.emailSent);
      setLinkOpen(true);
      await invalidate();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not resend the invite.");
    } finally {
      setBusyInvite(null);
    }
  }

  async function revoke(invite: Invite) {
    await apiDelete(
      `/api/v1/workspaces/${workspace.workspace?.id}/invites/${invite.id}`,
    );
    await invalidate();
    toast.success("Invite revoked");
    setRevokeTarget(null);
  }

  if (workspace.isLoading || members.isLoading) {
    return (
      <Page>
        <PageHeader eyebrow="Workspace" title="Members" />
        <div className="sc-card-grid">
          <Skeleton className="sc-project-skeleton" />
          <Skeleton className="sc-project-skeleton" />
        </div>
      </Page>
    );
  }

  if (!workspace.workspace) {
    return (
      <Page>
        <EmptyState icon={<Users size={24} />} title="Workspace not found" />
      </Page>
    );
  }

  return (
    <Page>
      <PageHeader
        eyebrow="Workspace"
        title="Members"
        description="Roles decide what people can see. Project grants narrow it further, optionally by environment."
        actions={
          canManage ? (
            <button type="button" className="sc-btn sc-btn--primary" onClick={() => setInviteOpen(true)}>
              <UserPlus size={16} /> Invite people
            </button>
          ) : undefined
        }
      />

      <SectionCard
        title="People"
        description={`${members.data?.length ?? 0} member${members.data?.length === 1 ? "" : "s"} in ${workspace.workspace.name}`}
      >
        {members.data?.length ? (
          <div className="sc-table-wrap">
            <table className="sc-table">
              <thead>
                <tr>
                  <th>Person</th>
                  <th>Role</th>
                  <th>Project grants</th>
                  <th>Joined</th>
                  {canManage ? <th className="sc-cell-actions">Actions</th> : null}
                </tr>
              </thead>
              <tbody>
                {members.data.map((member) => {
                  const isSelf = member.userId === me.data?.id;
                  const ownerLocked = member.role === "owner" && !isOwner;
                  return (
                    <tr key={member.userId}>
                      <td>
                        <div className="sc-person">
                          <Avatar name={member.name} size={32} />
                          <div>
                            <strong>
                              {member.name}
                              {isSelf ? <span className="sc-you">you</span> : null}
                            </strong>
                            <span>{member.email}</span>
                          </div>
                        </div>
                      </td>
                      <td>
                        {canManage && !ownerLocked ? (
                          <select
                            className="sc-select sc-select--sm"
                            value={member.role}
                            disabled={busyMember === member.userId}
                            onChange={(event) =>
                              void changeRole(member, event.target.value as WorkspaceRole)
                            }
                            aria-label={`Role for ${member.name}`}
                          >
                            {WORKSPACE_ROLES.filter(
                              (workspaceRole) => workspaceRole !== "owner" || isOwner,
                            ).map((workspaceRole) => (
                              <option key={workspaceRole} value={workspaceRole}>
                                {roleLabel(workspaceRole)}
                              </option>
                            ))}
                          </select>
                        ) : (
                          <RoleBadge role={member.role} />
                        )}
                      </td>
                      <td>
                        <div className="sc-chiprow">
                          {member.projectGrants.slice(0, 3).map((grant) => (
                            <Badge key={grant.projectId} tone="muted">
                              {grant.projectName} · {grant.role}
                            </Badge>
                          ))}
                          {member.projectGrants.length > 3 ? (
                            <Badge tone="muted">+{member.projectGrants.length - 3}</Badge>
                          ) : null}
                          {!member.projectGrants.length ? (
                            <span className="sc-cell-muted">No project grants</span>
                          ) : null}
                        </div>
                      </td>
                      <td className="sc-cell-muted">{formatRelative(member.joinedAt)}</td>
                      {canManage ? (
                        <td className="sc-cell-actions">
                          {!ownerLocked ? (
                            <button
                              type="button"
                              className="sc-iconbtn sc-iconbtn--danger"
                              aria-label={`Remove ${member.name}`}
                              onClick={() => setRemoveTarget(member)}
                            >
                              <X size={16} />
                            </button>
                          ) : null}
                        </td>
                      ) : null}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            compact
            icon={<Users size={22} />}
            title="No members yet"
            body="Invite the first teammate to this workspace."
          />
        )}
      </SectionCard>

      {canManage ? (
        <SectionCard
          title="Invites"
          description="Pending and recent invitations for this workspace."
        >
          {invites.isLoading ? (
            <Skeleton className="sc-skeleton--line" />
          ) : invites.data?.length ? (
            <div className="sc-table-wrap">
              <table className="sc-table">
                <thead>
                  <tr>
                    <th>Email</th>
                    <th>Workspace role</th>
                    <th>Project grants</th>
                    <th>Status</th>
                    <th>Expires</th>
                    <th className="sc-cell-actions">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {invites.data.map((invite) => {
                    const actionable = invite.status === "pending" || invite.status === "expired";
                    return (
                      <tr key={invite.id}>
                        <td>
                          <div className="sc-person">
                            <span className="sc-mailicon">
                              <MailPlus size={16} />
                            </span>
                            <div>
                              <strong>{invite.email}</strong>
                              {invite.invitedByName ? (
                                <span>invited by {invite.invitedByName}</span>
                              ) : null}
                            </div>
                          </div>
                        </td>
                        <td>
                          <RoleBadge role={invite.role} />
                        </td>
                        <td>
                          <div className="sc-chiprow">
                            {invite.grants.slice(0, 3).map((grant) => (
                              <Badge key={grant.projectId} tone="muted">
                                {grant.projectName} · {grant.role}
                              </Badge>
                            ))}
                            {invite.grants.length > 3 ? (
                              <Badge tone="muted">+{invite.grants.length - 3}</Badge>
                            ) : null}
                            {!invite.grants.length ? (
                              <span className="sc-cell-muted">No project grants</span>
                            ) : null}
                          </div>
                        </td>
                        <td>
                          <StatusBadge status={invite.status} />
                        </td>
                        <td className="sc-cell-muted">
                          {invite.status === "pending" ? formatMs(invite.expiresAt) : "—"}
                        </td>
                        <td className="sc-cell-actions">
                          {actionable ? (
                            <div className="sc-rowactions">
                              <button
                                type="button"
                                className="sc-iconbtn"
                                aria-label={`Resend invite to ${invite.email}`}
                                disabled={busyInvite === invite.id}
                                onClick={() => void resend(invite)}
                              >
                                <RotateCw size={15} />
                              </button>
                              <button
                                type="button"
                                className="sc-iconbtn sc-iconbtn--danger"
                                aria-label={`Revoke invite to ${invite.email}`}
                                onClick={() => setRevokeTarget(invite)}
                              >
                                <X size={16} />
                              </button>
                            </div>
                          ) : null}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState
              compact
              icon={<MailPlus size={22} />}
              title="No invites"
              body="Invite someone with the button above."
            />
          )}
        </SectionCard>
      ) : null}

      <InviteDialog
        workspaceId={workspace.workspace.id}
        projects={projects.data ?? []}
        canInviteOwner={isOwner}
        open={inviteOpen}
        onOpenChange={setInviteOpen}
      />
      <InviteLinkDialog
        open={linkOpen}
        onOpenChange={setLinkOpen}
        inviteUrl={linkUrl}
        emailSent={linkEmailSent}
      />
      <ConfirmDialog
        open={Boolean(removeTarget)}
        onOpenChange={(open) => !open && setRemoveTarget(null)}
        title="Remove member?"
        description={
          removeTarget
            ? `${removeTarget.name} will lose access to this workspace and its projects immediately.`
            : ""
        }
        confirmLabel="Remove member"
        destructive
        onConfirm={removeMember}
      />
      <ConfirmDialog
        open={Boolean(revokeTarget)}
        onOpenChange={(open) => !open && setRevokeTarget(null)}
        title="Revoke invite?"
        description={revokeTarget ? `The link sent to ${revokeTarget.email} will stop working.` : ""}
        confirmLabel="Revoke invite"
        destructive
        onConfirm={async () => {
          if (revokeTarget) await revoke(revokeTarget);
        }}
      />
    </Page>
  );
}
