"use client";

import { useQueryClient } from "@tanstack/react-query";
import {
  Copy,
  Download,
  Eye,
  EyeOff,
  FileUp,
  History,
  KeyRound,
  MoreHorizontal,
  Pencil,
  Plus,
  Search,
  Trash2,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";

import { DownloadDialog } from "@/components/secrets/DownloadDialog";
import { ImportDialog } from "@/components/secrets/ImportDialog";
import { SecretDialog } from "@/components/secrets/SecretDialog";
import { VersionDialog } from "@/components/secrets/VersionDialog";
import { Badge, EmptyState, Skeleton } from "@/components/ui/bits";
import { ConfirmDialog } from "@/components/ui/confirm";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown";
import { apiDelete, apiGet } from "@/lib/api-client";
import { copyText } from "@/lib/env";
import { formatMs, formatRelative } from "@/lib/format";
import { useSecrets } from "@/lib/queries";
import type { Environment, ProjectRole, Secret, SecretValue } from "@/lib/types";

export function SecretTable({
  projectId,
  projectSlug,
  environment,
  role,
}: {
  projectId: string;
  projectSlug: string;
  environment: Environment;
  role: ProjectRole;
}) {
  const secrets = useSecrets(projectId, environment.id);
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [revealed, setRevealed] = useState<Record<string, string>>({});
  const [editor, setEditor] = useState<{ secret: Secret | null } | null>(null);
  const [importOpen, setImportOpen] = useState(false);
  const [downloadOpen, setDownloadOpen] = useState(false);
  const [versionsSecret, setVersionsSecret] = useState<Secret | null>(null);
  const [deleteSecret, setDeleteSecret] = useState<Secret | null>(null);
  const timers = useRef<Record<string, number>>({});
  const canWrite = role === "admin" || role === "editor";

  useEffect(() => {
    const current = timers.current;
    return () => {
      Object.values(current).forEach((timer) => window.clearTimeout(timer));
    };
  }, []);

  function hide(key: string) {
    setRevealed((current) => {
      const next = { ...current };
      delete next[key];
      return next;
    });
    if (timers.current[key]) {
      window.clearTimeout(timers.current[key]);
      delete timers.current[key];
    }
  }

  async function reveal(secret: Secret): Promise<string | null> {
    if (revealed[secret.key] !== undefined) return revealed[secret.key];
    try {
      const result = await apiGet<SecretValue>(
        `/api/v1/projects/${projectId}/environments/${environment.id}/secrets/${encodeURIComponent(
          secret.key,
        )}`,
      );
      setRevealed((current) => ({ ...current, [secret.key]: result.value }));
      if (timers.current[secret.key]) window.clearTimeout(timers.current[secret.key]);
      timers.current[secret.key] = window.setTimeout(() => hide(secret.key), 30_000);
      await queryClient.invalidateQueries({ queryKey: ["audit"] });
      return result.value;
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not reveal the secret.");
      return null;
    }
  }

  async function copy(secret: Secret) {
    const value = await reveal(secret);
    if (value === null) return;
    try {
      await copyText(value);
      toast.success("Value copied");
    } catch {
      toast.error("Could not copy the value.");
    }
  }

  async function remove() {
    if (!deleteSecret) return;
    await apiDelete(
      `/api/v1/projects/${projectId}/environments/${environment.id}/secrets/${encodeURIComponent(
        deleteSecret.key,
      )}`,
    );
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["secrets", projectId, environment.id] }),
      queryClient.invalidateQueries({ queryKey: ["audit"] }),
    ]);
    toast.success("Secret deleted");
    setDeleteSecret(null);
  }

  const rows = useMemo(() => {
    const needle = search.trim().toLowerCase();
    return (secrets.data ?? []).filter((secret) => !needle || secret.key.toLowerCase().includes(needle));
  }, [secrets.data, search]);

  return (
    <section className="sc-card sc-secret-card">
      <div className="sc-table-toolbar">
        <div className="sc-search">
          <Search size={16} />
          <input
            className="sc-input sc-search-input"
            placeholder="Search keys…"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            aria-label="Search secret keys"
          />
        </div>
        <div className="sc-table-toolbar-actions">
          {canWrite ? (
            <button type="button" className="sc-btn sc-btn--ghost sc-btn--small" onClick={() => setImportOpen(true)}>
              <FileUp size={15} /> Import .env
            </button>
          ) : null}
          <button type="button" className="sc-btn sc-btn--ghost sc-btn--small" onClick={() => setDownloadOpen(true)}>
            <Download size={15} /> Download
          </button>
          {canWrite ? (
            <button type="button" className="sc-btn sc-btn--primary sc-btn--small" onClick={() => setEditor({ secret: null })}>
              <Plus size={15} /> New secret
            </button>
          ) : null}
        </div>
      </div>

      {secrets.isLoading ? (
        <div className="sc-stack sc-stack--pad">
          {[0, 1, 2, 3].map((index) => (
            <Skeleton key={index} className="sc-skeleton--row" />
          ))}
        </div>
      ) : rows.length ? (
        <div className="sc-table-wrap">
          <table className="sc-table sc-table--secrets">
            <thead>
              <tr>
                <th>Key</th>
                <th>Value</th>
                <th>Version</th>
                <th>Updated</th>
                <th className="sc-cell-actions" />
              </tr>
            </thead>
            <tbody>
              {rows.map((secret) => {
                const value = revealed[secret.key];
                return (
                  <tr key={secret.key}>
                    <td>
                      <code className="sc-secret-key">{secret.key}</code>
                      {secret.comment ? <p className="sc-secret-comment">{secret.comment}</p> : null}
                    </td>
                    <td>
                      {value !== undefined ? (
                        <div className="sc-value-revealed">
                          <code>{value}</code>
                          <button type="button" className="sc-iconbtn" aria-label="Copy value" onClick={() => void copy(secret)}>
                            <Copy size={14} />
                          </button>
                          <button type="button" className="sc-iconbtn" aria-label="Hide value" onClick={() => hide(secret.key)}>
                            <EyeOff size={15} />
                          </button>
                        </div>
                      ) : (
                        <div className="sc-value-masked">
                          <span className="sc-mask">••••••••</span>
                          <button type="button" className="sc-iconbtn" aria-label={`Reveal ${secret.key}`} onClick={() => void reveal(secret)}>
                            <Eye size={15} />
                          </button>
                        </div>
                      )}
                    </td>
                    <td>
                      <Badge tone="muted">v{secret.version ?? "—"}</Badge>
                    </td>
                    <td className="sc-cell-muted sc-nowrap" title={formatMs(secret.updatedAt)}>
                      {formatRelative(secret.updatedAt)}
                    </td>
                    <td className="sc-cell-actions">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <button type="button" className="sc-iconbtn" aria-label={`Actions for ${secret.key}`}>
                            <MoreHorizontal size={17} />
                          </button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent>
                          <DropdownMenuItem onSelect={() => void reveal(secret)}>
                            <Eye size={15} /> Reveal
                          </DropdownMenuItem>
                          <DropdownMenuItem onSelect={() => void copy(secret)}>
                            <Copy size={15} /> Copy value
                          </DropdownMenuItem>
                          {canWrite ? (
                            <>
                              <DropdownMenuItem onSelect={() => setEditor({ secret })}>
                                <Pencil size={15} /> Edit
                              </DropdownMenuItem>
                              <DropdownMenuSeparator />
                            </>
                          ) : null}
                          <DropdownMenuItem onSelect={() => setVersionsSecret(secret)}>
                            <History size={15} /> Version history
                          </DropdownMenuItem>
                          {canWrite ? (
                            <>
                              <DropdownMenuSeparator />
                              <DropdownMenuItem
                                className="sc-menu-item--danger"
                                onSelect={() => setDeleteSecret(secret)}
                              >
                                <Trash2 size={15} /> Delete
                              </DropdownMenuItem>
                            </>
                          ) : null}
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <EmptyState
          icon={<KeyRound size={24} />}
          title={search ? "No matching keys" : `No secrets in ${environment.name}`}
          body={search ? "Try a different search." : "Add the first key or import an existing .env."}
          action={
            !search && canWrite ? (
              <button type="button" className="sc-btn sc-btn--primary" onClick={() => setEditor({ secret: null })}>
                <Plus size={16} /> New secret
              </button>
            ) : undefined
          }
        />
      )}

      {secrets.error ? (
        <p className="sc-error sc-error--pad" role="alert">
          {secrets.error instanceof Error ? secrets.error.message : "Could not load secrets."}
        </p>
      ) : null}

      {editor ? (
        <SecretDialog
          key={editor.secret?.key ?? "new"}
          projectId={projectId}
          environmentId={environment.id}
          initial={editor.secret}
          open
          onOpenChange={(open) => !open && setEditor(null)}
        />
      ) : null}
      {importOpen ? (
        <ImportDialog
          projectId={projectId}
          environmentId={environment.id}
          open
          onOpenChange={(open) => !open && setImportOpen(false)}
        />
      ) : null}
      <DownloadDialog
        projectId={projectId}
        environmentId={environment.id}
        filename={`${projectSlug}-${environment.slug}.env`}
        open={downloadOpen}
        onOpenChange={setDownloadOpen}
      />
      {versionsSecret ? (
        <VersionDialog
          projectId={projectId}
          environmentId={environment.id}
          secret={versionsSecret}
          open
          onOpenChange={(open) => !open && setVersionsSecret(null)}
        />
      ) : null}
      <ConfirmDialog
        open={Boolean(deleteSecret)}
        onOpenChange={(open) => !open && setDeleteSecret(null)}
        title={`Delete ${deleteSecret?.key ?? "secret"}?`}
        description="The secret is soft-deleted and removed from the active list. Its versions remain in history."
        confirmLabel="Delete secret"
        destructive
        onConfirm={remove}
      />
    </section>
  );
}
