"use client";

import { useQueryClient } from "@tanstack/react-query";
import { KeyRound, LogOut, MonitorSmartphone, Save, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";

import { Avatar, Badge, EmptyState, RoleBadge, Skeleton } from "@/components/ui/bits";
import { ConfirmDialog } from "@/components/ui/confirm";
import { Page, PageHeader, SectionCard } from "@/components/ui/page";
import { apiDelete, apiPatch, apiPost } from "@/lib/api-client";
import { formatMs, formatRelative } from "@/lib/format";
import { useMe, useSessions, useWorkspaces } from "@/lib/queries";
import type { Me, Session } from "@/lib/types";

function ProfileForm({ me }: { me: Me }) {
  const [name, setName] = useState(me.name);
  const [busy, setBusy] = useState(false);
  const queryClient = useQueryClient();

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!name.trim()) return;
    setBusy(true);
    try {
      await apiPatch<Me>("/api/v1/me", { name: name.trim() });
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["me"] }),
        queryClient.invalidateQueries({ queryKey: ["members"] }),
      ]);
      toast.success("Profile updated");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not update the profile.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="sc-settings-form" onSubmit={submit}>
      <div className="sc-avatar-row">
        <Avatar name={me.name} size={48} />
        <div>
          <strong>{me.name}</strong>
          <span>{me.email}</span>
        </div>
      </div>
      <div className="sc-field">
        <label className="sc-label" htmlFor="settings-name">
          Display name
        </label>
        <input
          id="settings-name"
          className="sc-input"
          value={name}
          onChange={(event) => setName(event.target.value)}
          maxLength={200}
          required
        />
      </div>
      <div className="sc-field">
        <span className="sc-label">Email</span>
        <input className="sc-input" value={me.email} readOnly />
        <p className="sc-help">Email is managed by Elysiaa SSO.</p>
      </div>
      <button type="submit" className="sc-btn sc-btn--primary" disabled={busy || !name.trim()}>
        <Save size={16} /> {busy ? "Saving…" : "Save profile"}
      </button>
    </form>
  );
}

export function SettingsView() {
  const me = useMe();
  const sessions = useSessions();
  const workspaces = useWorkspaces();
  const [revokeSession, setRevokeSession] = useState<Session | null>(null);
  const queryClient = useQueryClient();

  async function signOut() {
    const data = await apiPost<{ logoutUrl: string | null }>("/api/auth/logout").catch(() => null);
    queryClient.clear();
    window.location.href = data?.logoutUrl ?? "/login";
  }

  async function revoke() {
    if (!revokeSession) return;
    await apiDelete(`/api/v1/me/sessions/${revokeSession.id}`);
    if (revokeSession.current) {
      // eslint-disable-next-line @next/next/no-location-assign-relative-destination
      window.location.href = "/login";
      return;
    }
    await queryClient.invalidateQueries({ queryKey: ["me", "sessions"] });
    toast.success("Session revoked");
    setRevokeSession(null);
  }

  return (
    <Page>
      <PageHeader
        eyebrow="Account"
        title="Settings"
        description="Your profile, web sessions, and the workspaces you belong to."
        actions={
          <button type="button" className="sc-btn sc-btn--ghost" onClick={() => void signOut()}>
            <LogOut size={16} /> Sign out
          </button>
        }
      />

      <div className="sc-settings-grid">
        <SectionCard title="Profile">
          {me.isLoading ? <Skeleton className="sc-skeleton--card" /> : me.data ? <ProfileForm me={me.data} /> : null}
        </SectionCard>

        <SectionCard title="Workspaces" description="Where you are a member.">
          {workspaces.isLoading ? (
            <Skeleton className="sc-skeleton--line" />
          ) : workspaces.data?.length ? (
            <div className="sc-workspace-list">
              {workspaces.data.map((workspace) => (
                <Link key={workspace.id} href={`/w/${workspace.slug}`} className="sc-workspace-row">
                  <span className="sc-workspace-mark">{workspace.name.slice(0, 1)}</span>
                  <span>
                    <strong>{workspace.name}</strong>
                    <span>{workspace.slug}</span>
                  </span>
                  <RoleBadge role={workspace.role} />
                </Link>
              ))}
            </div>
          ) : (
            <EmptyState compact icon={<ShieldCheck size={22} />} title="No workspaces" />
          )}
        </SectionCard>
      </div>

      <SectionCard
        title="Web sessions"
        description="Revoking a session signs that browser out. The current session is marked."
      >
        {sessions.isLoading ? (
          <Skeleton className="sc-skeleton--line" />
        ) : sessions.data?.length ? (
          <div className="sc-table-wrap">
            <table className="sc-table">
              <thead>
                <tr>
                  <th>Session</th>
                  <th>Created</th>
                  <th>Last used</th>
                  <th>Expires</th>
                  <th>IP</th>
                  <th className="sc-cell-actions" />
                </tr>
              </thead>
              <tbody>
                {sessions.data.map((session) => (
                  <tr key={session.id}>
                    <td>
                      <div className="sc-person sc-person--sm">
                        <span className="sc-mailicon">
                          <MonitorSmartphone size={16} />
                        </span>
                        <div>
                          <strong>{session.kind}</strong>
                          <span>{session.userAgent ?? "Unknown device"}</span>
                        </div>
                        {session.current ? <Badge tone="lime">current</Badge> : null}
                      </div>
                    </td>
                    <td className="sc-cell-muted">{formatMs(session.createdAt)}</td>
                    <td className="sc-cell-muted">
                      {session.lastUsedAt ? formatRelative(session.lastUsedAt) : "—"}
                    </td>
                    <td className="sc-cell-muted">{formatMs(session.expiresAt)}</td>
                    <td className="sc-cell-muted">{session.ip ?? "—"}</td>
                    <td className="sc-cell-actions">
                      <button
                        type="button"
                        className="sc-btn sc-btn--ghost sc-btn--small"
                        onClick={() => setRevokeSession(session)}
                      >
                        Revoke
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState compact icon={<KeyRound size={22} />} title="No active sessions" />
        )}
      </SectionCard>

      <SectionCard title="Command line" description="The CLI uses the Zitadel device flow, separately from this browser session.">
        <div className="sc-cli-hint">
          <KeyRound size={20} />
          <div>
            <strong>Sign in from your terminal</strong>
            <code className="sc-code-block">uv run --directory cli secria login</code>
          </div>
        </div>
      </SectionCard>

      <ConfirmDialog
        open={Boolean(revokeSession)}
        onOpenChange={(open) => !open && setRevokeSession(null)}
        title="Revoke this session?"
        description={
          revokeSession?.current
            ? "This is the current browser. Revoking it will sign you out."
            : "That browser will need to sign in again."
        }
        confirmLabel="Revoke session"
        destructive
        onConfirm={revoke}
      />
    </Page>
  );
}
