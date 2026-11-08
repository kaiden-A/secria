"use client";

import { ChevronDown, Filter, ScrollText, ShieldAlert } from "lucide-react";
import { useParams } from "next/navigation";
import { useState } from "react";

import { Avatar, Badge, EmptyState, Skeleton } from "@/components/ui/bits";
import { Page, PageHeader, SectionCard } from "@/components/ui/page";
import { AUDIT_ACTIONS, actionLabel, formatMs, metadataSummary } from "@/lib/format";
import { useAudit, useProjects, useWorkspace } from "@/lib/queries";
import type { AuditLog } from "@/lib/types";

function actionTone(action: string): "petrol" | "lime" | "danger" | "muted" {
  if (action.includes("deleted") || action.includes("revoked")) return "danger";
  if (action.includes("revealed") || action.includes("downloaded") || action.includes("created"))
    return "lime";
  if (action.includes("updated") || action.includes("push") || action.includes("granted"))
    return "petrol";
  return "muted";
}

function actorName(log: AuditLog): string {
  if (log.actorName) return log.actorName;
  if (log.actorType === "service_token") return "Service token";
  if (log.actorId) return log.actorId;
  return "System";
}

export function AuditView() {
  const params = useParams<{ ws: string }>();
  const wsSlug = params.ws;
  const workspace = useWorkspace(wsSlug);
  const projects = useProjects(workspace.workspace?.id);
  const canView = workspace.workspace?.role === "owner" || workspace.workspace?.role === "admin";
  const [filters, setFilters] = useState<{ project: string; actor: string; action: string }>({
    project: "",
    actor: "",
    action: "",
  });
  const [actorInput, setActorInput] = useState("");
  const audit = useAudit(canView ? workspace.workspace?.id : undefined, filters);

  if (workspace.isLoading) {
    return (
      <Page>
        <PageHeader eyebrow="Workspace" title="Audit log" />
        <Skeleton className="sc-skeleton-card" />
      </Page>
    );
  }

  if (!workspace.workspace) {
    return (
      <Page>
        <EmptyState icon={<ScrollText size={24} />} title="Workspace not found" />
      </Page>
    );
  }

  if (!canView) {
    return (
      <Page>
        <EmptyState
          icon={<ShieldAlert size={24} />}
          title="Admins only"
          body="The audit log is visible to workspace owners and admins."
        />
      </Page>
    );
  }

  const logs = audit.data?.pages.flatMap((page) => page.items) ?? [];

  return (
    <Page>
      <PageHeader
        eyebrow="Workspace"
        title="Audit log"
        description="Every reveal, download, change, invite, and membership action. Values are never recorded."
      />

      <SectionCard>
        <form
          className="sc-filterbar"
          onSubmit={(event) => {
            event.preventDefault();
            setFilters((current) => ({ ...current, actor: actorInput.trim() }));
          }}
        >
          <div className="sc-filter">
            <label className="sc-label" htmlFor="audit-project">
              Project
            </label>
            <select
              id="audit-project"
              className="sc-select sc-select--sm"
              value={filters.project}
              onChange={(event) =>
                setFilters((current) => ({ ...current, project: event.target.value }))
              }
            >
              <option value="">All projects</option>
              {projects.data?.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name}
                </option>
              ))}
            </select>
          </div>
          <div className="sc-filter">
            <label className="sc-label" htmlFor="audit-action">
              Action
            </label>
            <select
              id="audit-action"
              className="sc-select sc-select--sm"
              value={filters.action}
              onChange={(event) =>
                setFilters((current) => ({ ...current, action: event.target.value }))
              }
            >
              <option value="">All actions</option>
              {AUDIT_ACTIONS.map((action) => (
                <option key={action} value={action}>
                  {actionLabel(action)}
                </option>
              ))}
            </select>
          </div>
          <div className="sc-filter sc-filter--grow">
            <label className="sc-label" htmlFor="audit-actor">
              Actor
            </label>
            <input
              id="audit-actor"
              className="sc-input sc-input--sm"
              value={actorInput}
              onChange={(event) => setActorInput(event.target.value)}
              placeholder="Email or actor id"
            />
          </div>
          <div className="sc-filter-actions">
            <button type="submit" className="sc-btn sc-btn--ghost sc-btn--small">
              <Filter size={14} /> Apply
            </button>
            <button
              type="button"
              className="sc-btn sc-btn--ghost sc-btn--small"
              onClick={() => {
                setActorInput("");
                setFilters({ project: "", actor: "", action: "" });
              }}
            >
              Reset
            </button>
          </div>
        </form>

        {audit.isLoading ? (
          <div className="sc-stack">
            {[0, 1, 2, 3].map((index) => (
              <Skeleton key={index} className="sc-skeleton--row" />
            ))}
          </div>
        ) : logs.length ? (
          <>
            <div className="sc-table-wrap">
              <table className="sc-table sc-table--audit">
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>Actor</th>
                    <th>Action</th>
                    <th>Target</th>
                    <th>Details</th>
                    <th>IP</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map((log) => (
                    <tr key={log.id}>
                      <td className="sc-cell-muted sc-nowrap">{formatMs(log.createdAt)}</td>
                      <td>
                        <div className="sc-person sc-person--sm">
                          <Avatar name={actorName(log)} size={26} />
                          <div>
                            <strong>{actorName(log)}</strong>
                            <span>{log.actorEmail ?? log.actorType}</span>
                          </div>
                        </div>
                      </td>
                      <td>
                        <Badge tone={actionTone(log.action)}>{actionLabel(log.action)}</Badge>
                      </td>
                      <td>
                        <code className="sc-target">{log.target}</code>
                      </td>
                      <td className="sc-cell-muted">{metadataSummary(log.metadata) || "—"}</td>
                      <td className="sc-cell-muted sc-nowrap">{log.ip ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {audit.hasNextPage ? (
              <div className="sc-loadmore">
                <button
                  type="button"
                  className="sc-btn sc-btn--ghost"
                  onClick={() => void audit.fetchNextPage()}
                  disabled={audit.isFetchingNextPage}
                >
                  <ChevronDown size={15} />
                  {audit.isFetchingNextPage ? "Loading…" : "Load more"}
                </button>
              </div>
            ) : null}
          </>
        ) : (
          <EmptyState
            compact
            icon={<ScrollText size={22} />}
            title="No audit events"
            body="Actions in this workspace will appear here."
          />
        )}
      </SectionCard>

      {audit.error ? (
        <p className="sc-error" role="alert">
          {audit.error instanceof Error ? audit.error.message : "Could not load the audit log."}
        </p>
      ) : null}
      <p className="sc-mono sc-cell-muted">
        {filters.action ? actionLabel(filters.action) : "All actions"} · newest first
      </p>
    </Page>
  );
}
