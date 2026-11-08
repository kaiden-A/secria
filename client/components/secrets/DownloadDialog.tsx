"use client";

import { useQueryClient } from "@tanstack/react-query";
import { Download } from "lucide-react";
import { toast } from "sonner";

import { ConfirmDialog } from "@/components/ui/confirm";
import { apiFetch } from "@/lib/api-client";

export function DownloadDialog({
  projectId,
  environmentId,
  filename,
  open,
  onOpenChange,
}: {
  projectId: string;
  environmentId: string;
  filename: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const queryClient = useQueryClient();

  async function download() {
    const response = await apiFetch(
      `/api/v1/projects/${projectId}/environments/${environmentId}/secrets/download?format=env`,
    );
    if (!response.ok) {
      const body = (await response.json().catch(() => null)) as { error?: string } | null;
      throw new Error(body?.error ?? "Could not download the secrets.");
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
    await queryClient.invalidateQueries({ queryKey: ["audit"] });
    toast.success("Download started");
  }

  return (
    <ConfirmDialog
      open={open}
      onOpenChange={onOpenChange}
      title="Download plaintext .env?"
      description="The file contains raw secret values. The download is written to the audit log."
      confirmLabel="Download .env"
      onConfirm={download}
    >
      <div className="sc-notice sc-notice--warn">
        <Download size={17} />
        <span>Keep this file out of version control.</span>
      </div>
    </ConfirmDialog>
  );
}
