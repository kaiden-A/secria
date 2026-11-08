"use client";

import { useQueryClient } from "@tanstack/react-query";
import { KeyRound, Plus, ShieldOff } from "lucide-react";
import { useParams, usePathname, useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { ProjectShell, useProjectContext } from "@/components/ProjectShell";
import { TokenCreateDialog } from "@/components/TokenCreateDialog";
import { Badge, EmptyState, Skeleton } from "@/components/ui/bits";
import { ConfirmDialog } from "@/components/ui/confirm";
import { PageHeader, SectionCard } from "@/components/ui/page";
import { apiDelete } from "@/lib/api-client";
import { formatMs, formatRelative } from "@/lib/format";
import { useTokens } from "@/lib/queries";
import type { Environment, ServiceToken } from "@/lib/types";

function tokenStatus(token: ServiceToken): "active" | "revoked" | "expired" {
  if (token.revokedAt) return "revoked";
  if (token.expiresAt && token.expiresAt <= Date.now()) return "expired";
  return "active";
}

function TokensPanel() {
  const { project } = useProjectContext();
  const searchParams = useSearchParams();
  const pathname = usePathname();
  const router = useRouter();
  const [createOpen, setCreateOpen] = useState(false);
  const [revokeTarget, setRevokeTarget] = useState<ServiceToken | null>(null);
  const queryClient = useQueryClient();
  const canManage = project.role === "admin";

  const envSlug = searchParams.get("env");
  const environment: Environment | undefined =
    project.environments.find((item) => item.slug === envSlug) ??
    project.environments.find((item) => item.slug === "dev") ??
    project.environments[0];
  const tokens = useTokens(project.id, canManage ? environment?.id : undefined);

  async function revoke() {
    if (!revokeTarget || !environment) return;
    await apiDelete(
      `/api/v1/projects/${project.id}/environments/${environment.id}/service-tokens/${revokeTarget.id}`,
    );
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["tokens", project.id, environment.id] }),
      queryClient.invalidateQueries({ queryKey: ["audit"] }),
    ]);
    toast.success("Token revoked");
    setRevokeTarget(null);
  }

  if (!environment) {
    return (
      <EmptyState
        icon={<KeyRound size={24} />}
        title="No environments"
        body="Create an environment before creating service tokens."
      />
    );
  }

  return (
    <>
      <PageHeader
        eyebrow="Service tokens"
        title="Machine credentials"
        description="Scoped to one project and environment. Use them in CI through SECRIA_TOKEN."
        actions={
          canManage ? (
            <button type="button" className="sc-btn sc-btn--primary" onClick={() => setCreateOpen(true)}>
              <Plus size={16} /> New token
            </button>
          ) : undefined
        }
      />

      <div className="sc-envtabs-wrap">
        <div className="sc-envtabs" role="tablist" aria-label="Environment">
          {project.environments.map((item) => (
            <button
              key={item.id}
              type="button"
              role="tab"
              aria-selected={item.id === environment.id}
              className={`sc-envtab${item.id === environment.id ? " is-active" : ""}`}
              onClick={() => router.replace(`${pathname}?env=${item.slug}`, { scroll: false })}
            >
              {item.name}
            </button>
          ))}
        </div>
      </div>

      <SectionCard>
        {!canManage ? (
          <EmptyState
            compact
            icon={<KeyRound size={22} />}
            title="Admins only"
            body="Service tokens are created and revoked by project admins."
          />
        ) : tokens.isLoading ? (
          <div className="sc-stack">
            {[0, 1, 2].map((index) => (
              <Skeleton key={index} className="sc-skeleton--row" />
            ))}
          </div>
        ) : tokens.data?.length ? (
          <div className="sc-table-wrap">
            <table className="sc-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Access</th>
                  <th>Status</th>
                  <th>Last used</th>
                  <th>Expires</th>
                  <th>Created</th>
                  {canManage ? <th className="sc-cell-actions" /> : null}
                </tr>
              </thead>
              <tbody>
                {tokens.data.map((token) => {
                  const status = tokenStatus(token);
                  return (
                    <tr key={token.id}>
                      <td>
                        <div className="sc-person sc-person--sm">
                          <span className="sc-mailicon">
                            <KeyRound size={16} />
                          </span>
                          <strong>{token.name}</strong>
                        </div>
                      </td>
                      <td>
                        <Badge tone={token.access === "read_write" ? "petrol" : "muted"}>
                          {token.access === "read_write" ? "Read/write" : "Read only"}
                        </Badge>
                      </td>
                      <td>
                        <Badge tone={status === "active" ? "lime" : status === "expired" ? "danger" : "muted"}>
                          {status}
                        </Badge>
                      </td>
                      <td className="sc-cell-muted">
                        {token.lastUsedAt ? formatRelative(token.lastUsedAt) : "Never"}
                      </td>
                      <td className="sc-cell-muted">
                        {token.expiresAt ? formatMs(token.expiresAt) : "Never"}
                      </td>
                      <td className="sc-cell-muted">{formatMs(token.createdAt)}</td>
                      {canManage ? (
                        <td className="sc-cell-actions">
                          {status !== "revoked" ? (
                            <button
                              type="button"
                              className="sc-iconbtn sc-iconbtn--danger"
                              aria-label={`Revoke ${token.name}`}
                              onClick={() => setRevokeTarget(token)}
                            >
                              <ShieldOff size={16} />
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
            icon={<KeyRound size={22} />}
            title="No service tokens"
            body="Create one for CI, a server, or a deployment target."
          />
        )}
      </SectionCard>

      <TokenCreateDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        projectId={project.id}
        environmentId={environment.id}
        onCreated={() => {
          void Promise.all([
            queryClient.invalidateQueries({ queryKey: ["tokens", project.id, environment.id] }),
            queryClient.invalidateQueries({ queryKey: ["audit"] }),
          ]);
        }}
      />
      <ConfirmDialog
        open={Boolean(revokeTarget)}
        onOpenChange={(open) => !open && setRevokeTarget(null)}
        title={`Revoke ${revokeTarget?.name ?? "token"}?`}
        description="Any job using this token will stop working immediately."
        confirmLabel="Revoke token"
        destructive
        onConfirm={revoke}
      />
    </>
  );
}

export function TokensView() {
  const params = useParams<{ ws: string; project: string }>();
  return (
    <ProjectShell wsSlug={params.ws} projectSlug={params.project}>
      <TokensPanel />
    </ProjectShell>
  );
}
