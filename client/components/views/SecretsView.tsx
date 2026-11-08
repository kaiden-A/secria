"use client";

import { KeyRound } from "lucide-react";
import { useParams, usePathname, useRouter, useSearchParams } from "next/navigation";

import { ProjectShell, useProjectContext } from "@/components/ProjectShell";
import { SecretTable } from "@/components/secrets/SecretTable";
import { EmptyState } from "@/components/ui/bits";
import type { Environment } from "@/lib/types";

function SecretsPanel() {
  const { project } = useProjectContext();
  const searchParams = useSearchParams();
  const pathname = usePathname();
  const router = useRouter();
  const envSlug = searchParams.get("env");

  const environment: Environment | undefined =
    project.environments.find((item) => item.slug === envSlug) ??
    project.environments.find((item) => item.slug === "dev") ??
    project.environments[0];

  if (!environment) {
    return (
      <EmptyState
        icon={<KeyRound size={24} />}
        title="No environments"
        body="Create an environment before adding secrets."
      />
    );
  }

  return (
    <div className="sc-secrets-view">
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
        <p className="sc-envtabs-note sc-mono">
          {project.environments.length} environment{project.environments.length === 1 ? "" : "s"}
        </p>
      </div>
      <SecretTable
        key={environment.id}
        projectId={project.id}
        projectSlug={project.slug}
        environment={environment}
        role={project.role}
      />
    </div>
  );
}

export function SecretsView() {
  const params = useParams<{ ws: string; project: string }>();
  return (
    <ProjectShell wsSlug={params.ws} projectSlug={params.project}>
      <SecretsPanel />
    </ProjectShell>
  );
}
