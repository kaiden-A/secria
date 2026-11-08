export type WorkspaceRole = "owner" | "admin" | "member";
export type ProjectRole = "admin" | "editor" | "viewer";
export type ServiceAccess = "read" | "read_write";
export type InviteStatus = "pending" | "accepted" | "revoked" | "expired";

export type Me = {
  id: string;
  name: string;
  email: string;
  lastLoginAt: number | null;
};

export type Session = {
  id: string;
  kind: string;
  createdAt: number;
  lastUsedAt: number | null;
  expiresAt: number;
  ip: string | null;
  userAgent: string | null;
  current: boolean;
};

export type Workspace = {
  id: string;
  name: string;
  slug: string;
  role: WorkspaceRole;
  memberCount: number;
  projectCount: number;
  createdAt: number;
};

export type Environment = {
  id: string;
  name: string;
  slug: string;
  position: number;
  createdAt: number;
};

export type Project = {
  id: string;
  workspaceId: string;
  name: string;
  slug: string;
  description: string;
  role: ProjectRole;
  archivedAt: number | null;
  environmentCount: number;
  memberCount: number;
  createdAt: number;
  updatedAt: number;
};

export type ProjectDetail = Project & {
  environments: Environment[];
};

export type Secret = {
  key: string;
  version: number | null;
  comment: string;
  createdAt: number;
  updatedAt: number;
};

export type SecretValue = {
  key: string;
  value: string;
  version: number;
};

export type SecretVersion = {
  version: number;
  keyVersion: number;
  createdAt: number;
  createdBy: string | null;
  createdByName: string | null;
  createdByEmail: string | null;
  comment: string;
};

export type BulkResult = {
  added: number;
  updated: number;
  removed: number;
  unchanged: number;
};

export type DiffResult = {
  added: string[];
  changed: string[];
  removed: string[];
  unchanged: string[];
};

export type ProjectGrant = {
  projectId: string;
  projectName: string;
  role: ProjectRole;
};

export type WorkspaceMember = {
  userId: string;
  name: string;
  email: string;
  role: WorkspaceRole;
  joinedAt: number;
  projectGrants: ProjectGrant[];
};

export type ProjectMember = {
  userId: string;
  name: string;
  email: string;
  role: ProjectRole;
  environmentIds: string[] | null;
  joinedAt: number;
  source: "workspace" | "project";
};

export type Invite = {
  id: string;
  email: string;
  role: WorkspaceRole;
  grants: ProjectGrant[];
  invitedByName: string | null;
  status: InviteStatus;
  expiresAt: number;
  acceptedAt: number | null;
  revokedAt: number | null;
  createdAt: number;
};

export type InviteCreateResult = Invite & {
  inviteUrl: string;
  emailSent: boolean;
};

export type InviteResendResult = {
  inviteUrl: string;
  emailSent: boolean;
  expiresAt: number;
};

export type InvitePreview = {
  workspaceName: string;
  workspaceSlug: string;
  inviterName: string | null;
  email: string;
  role: WorkspaceRole;
  grants: ProjectGrant[];
  expiresAt: number;
};

export type InviteAcceptResult = {
  workspaceId: string;
  workspaceName: string;
  workspaceSlug: string;
};

export type AuditLog = {
  id: string;
  workspaceId: string;
  projectId: string | null;
  environmentId: string | null;
  actorType: string;
  actorId: string | null;
  actorName: string | null;
  actorEmail: string | null;
  action: string;
  target: string;
  metadata: Record<string, unknown>;
  ip: string | null;
  userAgent: string | null;
  createdAt: number;
};

export type AuditPage = {
  items: AuditLog[];
  nextCursor: string | null;
};

export type ServiceToken = {
  id: string;
  projectId: string;
  environmentId: string;
  name: string;
  access: ServiceAccess;
  expiresAt: number | null;
  lastUsedAt: number | null;
  revokedAt: number | null;
  createdAt: number;
};
