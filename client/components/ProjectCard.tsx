import { ArrowUpRight, FolderKanban, Layers, Users } from "lucide-react";
import Link from "next/link";

import { RoleBadge } from "@/components/ui/bits";
import { formatRelative } from "@/lib/format";
import type { Project } from "@/lib/types";

export function ProjectCard({ project, wsSlug }: { project: Project; wsSlug: string }) {
  return (
    <Link className="sc-project-card" href={`/w/${wsSlug}/p/${project.slug}`}>
      <div className="sc-project-card-top">
        <span className="sc-project-icon">
          <FolderKanban size={20} />
        </span>
        <RoleBadge role={project.role} />
        <ArrowUpRight size={16} className="sc-project-arrow" />
      </div>
      <h2>{project.name}</h2>
      <p>{project.description || "No description yet."}</p>
      <div className="sc-project-stats">
        <span>
          <Layers size={14} /> {project.environmentCount} envs
        </span>
        <span>
          <Users size={14} /> {project.memberCount} members
        </span>
        <span className="sc-project-updated">{formatRelative(project.updatedAt)}</span>
      </div>
    </Link>
  );
}
