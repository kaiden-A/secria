import { useInfiniteQuery, useQuery } from "@tanstack/react-query";

import { apiGet } from "@/lib/api-client";
import type {
  AuditPage,
  Invite,
  InvitePreview,
  Me,
  Project,
  ProjectDetail,
  ProjectMember,
  Secret,
  SecretVersion,
  ServiceToken,
  Session,
  Workspace,
  WorkspaceMember,
} from "@/lib/types";

export const queryKeys = {
  me: ["me"] as const,
  sessions: ["me", "sessions"] as const,
  workspaces: ["workspaces"] as const,
  projects: (workspaceId: string | undefined) => ["projects", workspaceId] as const,
  project: (projectId: string | undefined) => ["project", projectId] as const,
  secrets: (projectId: string | undefined, environmentId: string | undefined) =>
    ["secrets", projectId, environmentId] as const,
  versions: (projectId: string | undefined, environmentId: string | undefined, key: string) =>
    ["versions", projectId, environmentId, key] as const,
  workspaceMembers: (workspaceId: string | undefined) => ["members", workspaceId] as const,
  projectMembers: (projectId: string | undefined) => ["project-members", projectId] as const,
  invites: (workspaceId: string | undefined) => ["invites", workspaceId] as const,
  audit: (workspaceId: string | undefined) => ["audit", workspaceId] as const,
  tokens: (projectId: string | undefined, environmentId: string | undefined) =>
    ["tokens", projectId, environmentId] as const,
  invite: (token: string | undefined) => ["invite", token] as const,
};

export function useMe() {
  return useQuery({
    queryKey: queryKeys.me,
    queryFn: () => apiGet<Me>("/api/v1/me"),
  });
}

export function useSessions() {
  return useQuery({
    queryKey: queryKeys.sessions,
    queryFn: () => apiGet<Session[]>("/api/v1/me/sessions"),
  });
}

export function useWorkspaces() {
  return useQuery({
    queryKey: queryKeys.workspaces,
    queryFn: () => apiGet<Workspace[]>("/api/v1/workspaces"),
  });
}

export function useWorkspace(slug: string | undefined) {
  const query = useWorkspaces();
  const workspace = query.data?.find((item) => item.slug === slug) ?? null;
  return { ...query, workspace };
}

export function useProjects(workspaceId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.projects(workspaceId),
    queryFn: () => apiGet<Project[]>(`/api/v1/workspaces/${workspaceId}/projects`),
    enabled: Boolean(workspaceId),
  });
}

export function useProject(projectId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.project(projectId),
    queryFn: () => apiGet<ProjectDetail>(`/api/v1/projects/${projectId}`),
    enabled: Boolean(projectId),
  });
}

export function useSecrets(projectId: string | undefined, environmentId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.secrets(projectId, environmentId),
    queryFn: () =>
      apiGet<Secret[]>(
        `/api/v1/projects/${projectId}/environments/${environmentId}/secrets`,
      ),
    enabled: Boolean(projectId && environmentId),
  });
}

export function useVersions(
  projectId: string | undefined,
  environmentId: string | undefined,
  key: string,
  enabled: boolean,
) {
  return useQuery({
    queryKey: queryKeys.versions(projectId, environmentId, key),
    queryFn: () =>
      apiGet<SecretVersion[]>(
        `/api/v1/projects/${projectId}/environments/${environmentId}/secrets/${encodeURIComponent(key)}/versions`,
      ),
    enabled: Boolean(projectId && environmentId && key && enabled),
  });
}

export function useWorkspaceMembers(workspaceId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.workspaceMembers(workspaceId),
    queryFn: () => apiGet<WorkspaceMember[]>(`/api/v1/workspaces/${workspaceId}/members`),
    enabled: Boolean(workspaceId),
  });
}

export function useProjectMembers(projectId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.projectMembers(projectId),
    queryFn: () => apiGet<ProjectMember[]>(`/api/v1/projects/${projectId}/members`),
    enabled: Boolean(projectId),
  });
}

export function useInvites(workspaceId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: queryKeys.invites(workspaceId),
    queryFn: () => apiGet<Invite[]>(`/api/v1/workspaces/${workspaceId}/invites`),
    enabled: Boolean(workspaceId && enabled),
  });
}

export type AuditFilters = {
  project?: string;
  actor?: string;
  action?: string;
};

export function useAudit(workspaceId: string | undefined, filters: AuditFilters) {
  return useInfiniteQuery({
    queryKey: [...queryKeys.audit(workspaceId), filters],
    enabled: Boolean(workspaceId),
    initialPageParam: null as string | null,
    queryFn: ({ pageParam }) => {
      const params = new URLSearchParams();
      if (filters.project) params.set("project", filters.project);
      if (filters.actor) params.set("actor", filters.actor);
      if (filters.action) params.set("action", filters.action);
      if (pageParam) params.set("cursor", pageParam);
      params.set("limit", "50");
      return apiGet<AuditPage>(
        `/api/v1/workspaces/${workspaceId}/audit-logs?${params.toString()}`,
      );
    },
    getNextPageParam: (last) => last.nextCursor,
  });
}

export function useTokens(projectId: string | undefined, environmentId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.tokens(projectId, environmentId),
    queryFn: () =>
      apiGet<ServiceToken[]>(
        `/api/v1/projects/${projectId}/environments/${environmentId}/service-tokens`,
      ),
    enabled: Boolean(projectId && environmentId),
  });
}

export function useInvitePreview(token: string | undefined) {
  return useQuery({
    queryKey: queryKeys.invite(token),
    queryFn: () => apiGet<InvitePreview>(`/api/v1/invites/${encodeURIComponent(token ?? "")}`),
    enabled: Boolean(token),
    retry: false,
  });
}
