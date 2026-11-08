"use client";

import { ArrowRight, KeyRound, Mail, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { Logo } from "@/components/Logo";
import { ThemeToggle } from "@/components/ThemeToggle";
import { Badge, RoleBadge, Skeleton } from "@/components/ui/bits";
import { ApiError, apiPost } from "@/lib/api-client";
import { formatMs } from "@/lib/format";
import { useInvitePreview } from "@/lib/queries";
import type { InviteAcceptResult } from "@/lib/types";

export function InviteView() {
  const params = useParams<{ token: string }>();
  const token = params.token;
  const preview = useInvitePreview(token);
  const router = useRouter();
  const [busy, setBusy] = useState(false);

  async function accept() {
    setBusy(true);
    try {
      const result = await apiPost<InviteAcceptResult>(
        `/api/v1/invites/${encodeURIComponent(token)}/accept`,
      );
      toast.success(`Joined ${result.workspaceName}`);
      router.push(`/w/${result.workspaceSlug}`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not accept the invite.");
    } finally {
      setBusy(false);
    }
  }

  const unauthorized = preview.error instanceof ApiError && preview.error.status === 401;

  return (
    <main className="sc-invite-page">
      <div className="sc-invite-top">
        <Link href="/" className="sc-brand">
          <Logo size={30} />
          <span className="sc-brand-word">SECRIA</span>
        </Link>
        <div className="sc-invite-top-right">
          <span className="sc-mono sc-cell-muted">A sealed invitation</span>
          <ThemeToggle />
        </div>
      </div>

      <section className="sc-invite-card">
        <div className="sc-invite-mark">
          <Mail size={22} />
        </div>
        {preview.isLoading ? (
          <div className="sc-stack">
            <Skeleton className="sc-skeleton--eyebrow" />
            <Skeleton className="sc-skeleton--title" />
            <Skeleton className="sc-skeleton--line" />
            <Skeleton className="sc-skeleton--row" />
          </div>
        ) : unauthorized ? (
          <>
            <p className="sc-eyebrow">Invitation</p>
            <h1>Sign in to open this invite.</h1>
            <p className="sc-invite-sub">
              Use the same email address the invite was sent to.
            </p>
            <Link
              className="sc-btn sc-btn--primary sc-btn--lg"
              href={`/login?next=${encodeURIComponent(`/invite/${token}`)}`}
            >
              Continue to sign in <ArrowRight size={17} />
            </Link>
          </>
        ) : preview.error || !preview.data ? (
          <>
            <p className="sc-eyebrow">Invitation</p>
            <h1>This invite isn&rsquo;t available.</h1>
            <p className="sc-invite-sub">
              {preview.error instanceof Error
                ? preview.error.message
                : "It may have expired, been revoked, or already been accepted."}
            </p>
            <Link className="sc-btn sc-btn--ghost" href="/">
              Back to Secria
            </Link>
          </>
        ) : (
          <>
            <p className="sc-eyebrow">
              <span className="sc-signal-dot" /> You&rsquo;re invited
            </p>
            <h1>{preview.data.workspaceName}</h1>
            <p className="sc-invite-sub">
              {preview.data.inviterName ? (
                <>
                  <strong>{preview.data.inviterName}</strong> invited you to join as{" "}
                  <strong>{preview.data.role}</strong>.
                </>
              ) : (
                <>You&rsquo;ve been invited to join as <strong>{preview.data.role}</strong>.</>
              )}
            </p>

            <div className="sc-invite-meta">
              <RoleBadge role={preview.data.role} />
              <span className="sc-mono">expires {formatMs(preview.data.expiresAt)}</span>
            </div>

            {preview.data.grants.length ? (
              <div className="sc-invite-grants">
                <p className="sc-label">Project access</p>
                {preview.data.grants.map((grant) => (
                  <div className="sc-invite-grant" key={grant.projectId}>
                    <span>
                      <KeyRound size={15} /> {grant.projectName}
                    </span>
                    <Badge tone="muted">{grant.role}</Badge>
                  </div>
                ))}
              </div>
            ) : null}

            <button
              type="button"
              className="sc-btn sc-btn--primary sc-btn--lg"
              onClick={() => void accept()}
              disabled={busy}
            >
              {busy ? "Joining…" : "Accept invitation"} <ArrowRight size={17} />
            </button>
            <p className="sc-invite-foot">
              <ShieldCheck size={14} /> This invite works only for {preview.data.email}.
            </p>
          </>
        )}
      </section>
    </main>
  );
}
