"use client";

import { FolderKanban, Plus } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

import { CreateProjectDialog } from "@/components/CreateProjectDialog";
import { ProjectCard } from "@/components/ProjectCard";
import { EmptyState, Skeleton } from "@/components/ui/bits";
import { Page, PageHeader, SectionCard } from "@/components/ui/page";
import { useProjects, useWorkspace } from "@/lib/queries";

export function ProjectsView() {
  const params = useParams<{ ws: string }>();
  const wsSlug = params.ws;
  const workspace = useWorkspace(wsSlug);
  const projects = useProjects(workspace.workspace?.id);
  const [open, setOpen] = useState(false);

  if (workspace.isLoading) {
    return (
      <Page>
        <PageHeader eyebrow="Workspace" title="Projects" />
        <div className="sc-card-grid">
          {[0, 1, 2].map((index) => (
            <Skeleton key={index} className="sc-project-skeleton" />
          ))}
        </div>
      </Page>
    );
  }

  if (!workspace.workspace) {
    return (
      <Page>
        <EmptyState
          icon={<FolderKanban size={24} />}
          title="Workspace not found"
          body="It may have been deleted, or your account does not have access."
          action={
            <Link className="sc-btn sc-btn--ghost" href="/">
              Back to Secria
            </Link>
          }
        />
      </Page>
    );
  }

  const canCreate = workspace.workspace.role === "owner" || workspace.workspace.role === "admin";

  return (
    <Page>
      <PageHeader
        eyebrow="Workspace"
        title={workspace.workspace.name}
        description="Projects keep their own environments, members, keys, and audit trail."
        actions={
          canCreate ? (
            <button type="button" className="sc-btn sc-btn--primary" onClick={() => setOpen(true)}>
              <Plus size={16} /> New project
            </button>
          ) : undefined
        }
      />

      <SectionCard>
        {projects.isLoading ? (
          <div className="sc-card-grid">
            {[0, 1, 2].map((index) => (
              <Skeleton key={index} className="sc-project-skeleton" />
            ))}
          </div>
        ) : projects.data?.length ? (
          <div className="sc-card-grid">
            {projects.data.map((project) => (
              <ProjectCard key={project.id} project={project} wsSlug={wsSlug} />
            ))}
          </div>
        ) : (
          <EmptyState
            icon={<FolderKanban size={24} />}
            title="No projects yet"
            body={
              canCreate
                ? "Create the first project and Secria will provision its environments and encryption key."
                : "A workspace admin needs to create a project and grant you access."
            }
            action={
              canCreate ? (
                <button type="button" className="sc-btn sc-btn--primary" onClick={() => setOpen(true)}>
                  <Plus size={16} /> Create project
                </button>
              ) : undefined
            }
          />
        )}
      </SectionCard>

      <CreateProjectDialog
        workspaceId={workspace.workspace.id}
        workspaceSlug={wsSlug}
        open={open}
        onOpenChange={setOpen}
      />
    </Page>
  );
}
