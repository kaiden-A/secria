"use client";

import { FolderKanban, Plus } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { CreateWorkspaceDialog } from "@/components/CreateWorkspaceDialog";
import { EmptyState, RoleBadge, Skeleton } from "@/components/ui/bits";
import { Page, PageHeader, SectionCard } from "@/components/ui/page";
import { useWorkspaces } from "@/lib/queries";

export function WorkspaceIndexView() {
  const workspaces = useWorkspaces();
  const router = useRouter();
  const [open, setOpen] = useState(false);

  // A single workspace is the common case: go straight to its projects.
  useEffect(() => {
    if (workspaces.data?.length === 1) {
      router.replace(`/w/${workspaces.data[0].slug}`);
    }
  }, [workspaces.data, router]);

  if (workspaces.isLoading) {
    return (
      <Page>
        <PageHeader eyebrow="Secria" title="Workspaces" />
        <div className="sc-card-grid">
          {[0, 1].map((index) => (
            <Skeleton key={index} className="sc-project-skeleton" />
          ))}
        </div>
      </Page>
    );
  }

  return (
    <Page>
      <PageHeader
        eyebrow="Secria"
        title="Workspaces"
        description="Choose a workspace, or create one to start a project."
        actions={
          <button type="button" className="sc-btn sc-btn--primary" onClick={() => setOpen(true)}>
            <Plus size={16} /> New workspace
          </button>
        }
      />

      <SectionCard>
        {workspaces.data?.length ? (
          <div className="sc-card-grid">
            {workspaces.data.map((workspace) => (
              <Link
                key={workspace.id}
                href={`/w/${workspace.slug}`}
                className="sc-project-card"
              >
                <div className="sc-project-card-top">
                  <span className="sc-project-icon">
                    <FolderKanban size={20} />
                  </span>
                  <RoleBadge role={workspace.role} />
                </div>
                <h2>{workspace.name}</h2>
                <p className="sc-mono">{workspace.slug}</p>
                <div className="sc-project-stats">
                  <span>{workspace.projectCount} projects</span>
                  <span>{workspace.memberCount} members</span>
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <EmptyState
            icon={<FolderKanban size={24} />}
            title="No workspaces yet"
            body="Create a workspace, then add a project and its environments."
            action={
              <button type="button" className="sc-btn sc-btn--primary" onClick={() => setOpen(true)}>
                <Plus size={16} /> Create workspace
              </button>
            }
          />
        )}
      </SectionCard>

      <CreateWorkspaceDialog open={open} onOpenChange={setOpen} />
    </Page>
  );
}
