"use client";

import { useQueryClient } from "@tanstack/react-query";
import {
  ChevronDown,
  FolderKanban,
  LogOut,
  Plus,
  ScrollText,
  Settings,
  Users,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";

import { CreateWorkspaceDialog } from "@/components/CreateWorkspaceDialog";
import { Logo } from "@/components/Logo";
import { Avatar, RoleBadge, Skeleton } from "@/components/ui/bits";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown";
import { Breadcrumbs } from "@/components/ui/page";
import { apiPost } from "@/lib/api-client";
import { initials, titleCase } from "@/lib/format";
import { useMe, useWorkspaces } from "@/lib/queries";

function sectionLabel(pathname: string): string {
  if (pathname.endsWith("/members")) return "Members";
  if (pathname.endsWith("/audit")) return "Audit";
  if (pathname.endsWith("/access")) return "Access";
  if (pathname.endsWith("/tokens")) return "Tokens";
  if (pathname.includes("/p/")) return "Secrets";
  if (pathname === "/settings") return "Settings";
  return "Projects";
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const queryClient = useQueryClient();
  const me = useMe();
  const workspaces = useWorkspaces();
  const [workspaceOpen, setWorkspaceOpen] = useState(false);

  const wsSlug = pathname.match(/^\/w\/([^/]+)/)?.[1];
  const projectSlug = pathname.match(/^\/w\/[^/]+\/p\/([^/]+)/)?.[1];
  const workspace = workspaces.data?.find((item) => item.slug === wsSlug) ?? null;
  const canSeeAudit = workspace?.role === "owner" || workspace?.role === "admin";

  const nav = wsSlug
    ? [
        { href: `/w/${wsSlug}`, label: "Projects", icon: FolderKanban },
        { href: `/w/${wsSlug}/members`, label: "Members", icon: Users },
        ...(canSeeAudit
          ? [{ href: `/w/${wsSlug}/audit`, label: "Audit", icon: ScrollText }]
          : []),
      ]
    : [];

  const crumbs = (() => {
    if (pathname === "/settings") return [{ label: "Settings" }];
    if (!wsSlug) return [{ label: "Secria" }];
    const items: { label: string; href?: string }[] = [
      { label: workspace?.name ?? wsSlug, href: `/w/${wsSlug}` },
    ];
    if (projectSlug) {
      items.push({
        label: titleCase(projectSlug.replace(/-/g, " ")),
        href: `/w/${wsSlug}/p/${projectSlug}`,
      });
    }
    items.push({ label: sectionLabel(pathname) });
    return items;
  })();

  async function signOut() {
    const data = await apiPost<{ logoutUrl: string | null }>("/api/auth/logout").catch(() => null);
    queryClient.clear();
    window.location.href = data?.logoutUrl ?? "/login";
  }

  return (
    <div className="sc-app">
      <aside className="sc-rail" aria-label="Primary">
        <div className="sc-rail-top">
          <Link href={wsSlug ? `/w/${wsSlug}` : "/"} className="sc-brand sc-brand--on-dark sc-rail-brand">
            <Logo size={30} />
            <span className="sc-brand-word">SECRIA</span>
          </Link>

          <div className="sc-workspace-wrap">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button type="button" className="sc-workspace-btn">
                  <span className="sc-workspace-mark">
                    {workspace ? initials(workspace.name) : "S"}
                  </span>
                  <span className="sc-workspace-text">
                    <strong>
                      {workspace?.name ??
                        (pathname === "/w" ? "Choose a workspace" : "No workspace")}
                    </strong>
                    <span>
                      {workspace?.slug ??
                        (pathname === "/w"
                          ? "Select from the list"
                          : "Create your first workspace")}
                    </span>
                  </span>
                  <ChevronDown size={14} className="sc-workspace-chevron" />
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start" className="sc-workspace-menu">
                <DropdownMenuLabel>Workspaces</DropdownMenuLabel>
                {workspaces.data?.map((item) => (
                  <DropdownMenuItem
                    key={item.id}
                    onSelect={() => router.push(`/w/${item.slug}`)}
                  >
                    <span className="sc-menu-workspace-mark">{initials(item.name)}</span>
                    <span className="sc-menu-workspace-text">
                      <strong>{item.name}</strong>
                      <span>{item.slug}</span>
                    </span>
                    {item.id === workspace?.id ? <span className="sc-menu-current">•</span> : null}
                  </DropdownMenuItem>
                ))}
                {workspaces.isLoading ? <Skeleton className="sc-menu-skeleton" /> : null}
                <DropdownMenuSeparator />
                <DropdownMenuItem onSelect={() => setWorkspaceOpen(true)}>
                  <Plus size={15} />
                  New workspace
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
            {!workspaces.isLoading && !workspaces.data?.length ? (
              <button
                type="button"
                className="sc-rail-create"
                onClick={() => setWorkspaceOpen(true)}
              >
                <Plus size={14} /> Create a workspace
              </button>
            ) : null}
          </div>

          <nav className="sc-rail-nav" aria-label="Workspace">
            {nav.map((item) => {
              const active =
                pathname === item.href ||
                (item.href !== `/w/${wsSlug}` && pathname.startsWith(`${item.href}/`));
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`sc-rail-link${active ? " is-active" : ""}`}
                >
                  <item.icon size={17} />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>
        </div>

        <div className="sc-rail-bottom">
          <Link
            href="/settings"
            className={`sc-rail-link${pathname === "/settings" ? " is-active" : ""}`}
          >
            <Settings size={17} />
            <span>Settings</span>
          </Link>
        </div>
      </aside>

      <div className="sc-main">
        <header className="sc-topbar">
          <div className="sc-topbar-left">
            <Breadcrumbs items={crumbs} />
          </div>
          <div className="sc-topbar-right">
            {workspace ? <RoleBadge role={workspace.role} /> : null}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button type="button" className="sc-userbtn" aria-label="Account">
                  {me.data ? <Avatar name={me.data.name} size={30} /> : <Skeleton className="sc-avatar-skeleton" />}
                  <span className="sc-userbtn-text">
                    <strong>{me.data?.name ?? "Your account"}</strong>
                    <span>{me.data?.email ?? ""}</span>
                  </span>
                  <ChevronDown size={14} />
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="sc-usermenu">
                <DropdownMenuLabel>
                  <strong>{me.data?.name ?? "Your account"}</strong>
                  <span>{me.data?.email ?? ""}</span>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem onSelect={() => router.push("/settings")}>
                  <Settings size={15} />
                  Settings
                </DropdownMenuItem>
                <DropdownMenuItem onSelect={() => void signOut()}>
                  <LogOut size={15} />
                  Sign out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </header>

        <main className="sc-view">{children}</main>
      </div>

      <CreateWorkspaceDialog open={workspaceOpen} onOpenChange={setWorkspaceOpen} />
    </div>
  );
}
