"use client";

import { FolderKanban, Lock } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { createContext, useContext } from "react";
import type { ReactNode } from "react";

import { EmptyState, RoleBadge, Skeleton } from "@/components/ui/bits";
import { Page } from "@/components/ui/page";
import { formatRelative } from "@/lib/format";
import { useProject, useProjects, useWorkspace } from "@/lib/queries";
import type { ProjectDetail, Workspace } from "@/lib/types";

type ProjectContextValue = {
  workspace: Workspace;
  project: ProjectDetail;
};

const ProjectContext = createContext<ProjectContextValue | null>(null);

export function useProjectContext(): ProjectContextValue {
  const context = useContext(ProjectContext);
  if (!context) throw new Error("useProjectContext must be used inside ProjectShell");
  return context;
}

export function ProjectShell({
  wsSlug,
  projectSlug,
  children,
}: {
  wsSlug: string;
  projectSlug: string;
  children: ReactNode;
}) {
  const pathname = usePathname();
  const workspace = useWorkspace(wsSlug);
  const projects = useProjects(workspace.workspace?.id);
  const summary = projects.data?.find((item) => item.slug === projectSlug) ?? null;
  const project = useProject(summary?.id);
  const loadedWorkspace = workspace.workspace;
  const loadedProject = project.data;

  if (workspace.isLoading || projects.isLoading || project.isLoading) {
    return (
      <Page>
        <div className="sc-page-head">
          <div>
            <Skeleton className="sc-skeleton--eyebrow" />
            <Skeleton className="sc-skeleton--title" />
            <Skeleton className="sc-skeleton--line" />
          </div>
        </div>
        <div className="sc-skeleton-card" />
      </Page>
    );
  }

  if (!loadedWorkspace || !summary || !loadedProject) {
    return (
      <Page>
        <EmptyState
          icon={<FolderKanban size={24} />}
          title="Project not found"
          body="It may have been archived, deleted, or you may not have access."
          action={
            <Link className="sc-btn sc-btn--ghost" href={`/w/${wsSlug}`}>
              Back to projects
            </Link>
          }
        />
      </Page>
    );
  }

  const tabs = [
    { href: `/w/${wsSlug}/p/${projectSlug}`, label: "Secrets" },
    { href: `/w/${wsSlug}/p/${projectSlug}/access`, label: "Access" },
    { href: `/w/${wsSlug}/p/${projectSlug}/tokens`, label: "Tokens" },
  ];

  return (
    <ProjectContext.Provider value={{ workspace: loadedWorkspace, project: loadedProject }}>
      <Page>
        <header className="sc-project-head">
          <div className="sc-project-headcopy">
            <div className="sc-project-title-row">
              <h1 className="sc-page-title">{loadedProject.name}</h1>
              <RoleBadge role={loadedProject.role} />
              {loadedProject.archivedAt ? <span className="sc-badge sc-badge--muted">Archived</span> : null}
            </div>
            <p className="sc-page-sub">
              {loadedProject.description || "No description yet."}
            </p>
            <p className="sc-project-stamp sc-mono">
              <Lock size={12} /> {loadedProject.environments.length} environments ·{" "}
              {loadedProject.memberCount} direct members · updated{" "}
              {formatRelative(loadedProject.updatedAt)}
            </p>
          </div>
        </header>

        <nav className="sc-project-tabs" aria-label="Project">
          {tabs.map((tab) => (
            <Link
              key={tab.href}
              href={tab.href}
              className={`sc-project-tab${
                pathname === tab.href || (tab.label !== "Secrets" && pathname.startsWith(tab.href))
                  ? " is-active"
                  : ""
              }`}
            >
              {tab.label}
            </Link>
          ))}
        </nav>

        {children}
      </Page>
    </ProjectContext.Provider>
  );
}
