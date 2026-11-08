"use client";

import { useQueryClient } from "@tanstack/react-query";
import { History, RotateCcw } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Badge, EmptyState, Skeleton } from "@/components/ui/bits";
import { ConfirmDialog } from "@/components/ui/confirm";
import { Dialog, DialogBody, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { apiPost } from "@/lib/api-client";
import { formatMs } from "@/lib/format";
import { useVersions } from "@/lib/queries";
import type { Secret } from "@/lib/types";

export function VersionDialog({
  projectId,
  environmentId,
  secret,
  open,
  onOpenChange,
}: {
  projectId: string;
  environmentId: string;
  secret: Secret;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const versions = useVersions(projectId, environmentId, secret.key, open);
  const [rollbackVersion, setRollbackVersion] = useState<number | null>(null);
  const queryClient = useQueryClient();

  async function rollback() {
    if (rollbackVersion === null) return;
    await apiPost(
      `/api/v1/projects/${projectId}/environments/${environmentId}/secrets/${encodeURIComponent(
        secret.key,
      )}/rollback`,
      { version: rollbackVersion },
    );
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["secrets", projectId, environmentId] }),
      queryClient.invalidateQueries({
        queryKey: ["versions", projectId, environmentId, secret.key],
      }),
      queryClient.invalidateQueries({ queryKey: ["audit"] }),
    ]);
    toast.success("Secret rolled back");
    setRollbackVersion(null);
  }

  const currentVersion = versions.data?.[0]?.version;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sc-dialog--wide">
        <DialogHeader>
          <DialogTitle>Version history · {secret.key}</DialogTitle>
          <DialogDescription>
            Rollback writes a new version from the old plaintext; history is never re-pointed.
          </DialogDescription>
        </DialogHeader>
        <DialogBody>
          {versions.isLoading ? (
            <div className="sc-stack">
              {[0, 1, 2].map((index) => (
                <Skeleton key={index} className="sc-skeleton--row" />
              ))}
            </div>
          ) : versions.data?.length ? (
            <div className="sc-table-wrap">
              <table className="sc-table">
                <thead>
                  <tr>
                    <th>Version</th>
                    <th>Created</th>
                    <th>Author</th>
                    <th>Comment</th>
                    <th className="sc-cell-actions" />
                  </tr>
                </thead>
                <tbody>
                  {versions.data.map((version) => (
                    <tr key={version.version}>
                      <td>
                        <div className="sc-chiprow">
                          <Badge tone="muted">v{version.version}</Badge>
                          {version.version === currentVersion ? <Badge tone="lime">current</Badge> : null}
                        </div>
                      </td>
                      <td className="sc-cell-muted">{formatMs(version.createdAt)}</td>
                      <td>
                        <span className="sc-cell-muted">
                          {version.createdByName ?? version.createdByEmail ?? "—"}
                        </span>
                      </td>
                      <td className="sc-cell-muted">{version.comment || "—"}</td>
                      <td className="sc-cell-actions">
                        {version.version !== currentVersion ? (
                          <button
                            type="button"
                            className="sc-btn sc-btn--ghost sc-btn--small"
                            onClick={() => setRollbackVersion(version.version)}
                          >
                            <RotateCcw size={14} /> Roll back
                          </button>
                        ) : null}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState compact icon={<History size={22} />} title="No versions" />
          )}
          {versions.error ? (
            <p className="sc-error" role="alert">
              {versions.error instanceof Error ? versions.error.message : "Could not load versions."}
            </p>
          ) : null}
        </DialogBody>
      </DialogContent>
      <ConfirmDialog
        open={rollbackVersion !== null}
        onOpenChange={(next) => !next && setRollbackVersion(null)}
        title={`Roll back to v${rollbackVersion ?? ""}?`}
        description="Secria will create a new current version from that old value. Nothing is lost."
        confirmLabel="Roll back"
        onConfirm={rollback}
      />
    </Dialog>
  );
}
