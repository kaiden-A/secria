import type { Metadata } from "next";
import Link from "next/link";

import { Check, Lock, Shield } from "@/components/Icons";
import { Logo } from "@/components/Logo";

export const metadata: Metadata = {
  title: "Sign in",
  description: "Sign in to Secria with Elysiaa SSO.",
};

function safeNext(value: string | undefined): string {
  if (!value || !value.startsWith("/") || value.startsWith("//")) return "/";
  return value;
}

const POINTS = [
  "Your password never touches Secria.",
  "Secrets stay encrypted at rest and in transit.",
  "Every reveal leaves a receipt in the audit log.",
];

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ next?: string; error?: string }>;
}) {
  const params = await searchParams;
  const next = safeNext(typeof params.next === "string" ? params.next : undefined);
  const error = typeof params.error === "string" ? params.error : null;

  return (
    <main className="sc-login">
      <aside className="sc-login-aside">
        <Link href="/" className="sc-brand sc-brand--on-dark">
          <Logo size={32} />
          <span className="sc-brand-word">SECRIA</span>
        </Link>

        <div className="sc-login-copy">
          <p className="sc-eyebrow sc-eyebrow--on-dark">
            <span className="sc-signal-dot" aria-hidden="true" />
            Identity, handled
          </p>
          <h2>One door. The right people. Nothing else.</h2>
          <p>
            Secria uses Elysiaa SSO for identity and keeps authorization in its own
            database. A valid sign-in is only the beginning — every request still checks
            the workspace and project.
          </p>
          <ul className="sc-login-points">
            {POINTS.map((point) => (
              <li key={point}>
                <Check size={16} />
                {point}
              </li>
            ))}
          </ul>
        </div>

        <p className="sc-login-aside-foot">
          <Lock size={14} />
          OIDC Authorization Code + PKCE. No client secret.
        </p>
      </aside>

      <section className="sc-login-main">
        <div className="sc-login-card">
          <span className="sc-login-icon">
            <Shield size={22} />
          </span>
          <h1>Sign in to Secria</h1>
          <p className="sc-login-sub">
            Use the email your team knows you by. We&rsquo;ll take you to Elysiaa to confirm
            it&rsquo;s you.
          </p>

          {error ? (
            <p className="sc-error" role="alert">
              {error}
            </p>
          ) : null}

          <form action="/api/auth/login" method="get">
            <input type="hidden" name="next" value={next} />
            <div className="sc-field">
              <label className="sc-label" htmlFor="email">
                Email
              </label>
              <input
                id="email"
                name="login_hint"
                type="email"
                required
                autoComplete="email"
                placeholder="you@company.com"
                className="sc-input"
              />
            </div>
            <button type="submit" className="sc-btn sc-btn--primary sc-btn--block">
              Continue with Elysiaa SSO
            </button>
          </form>

          <div className="sc-divider">
            <span />
            <em>one account, all your workspaces</em>
            <span />
          </div>

          <p className="sc-login-foot">
            New here? An invite from a workspace admin is all you need. Ask them to send
            one to this email.
          </p>
        </div>

        <Link className="sc-login-back" href="/">
          ← Back to the landing page
        </Link>
      </section>
    </main>
  );
}
