import Link from "next/link";

import { ArrowRight } from "@/components/Icons";
import { Logo } from "@/components/Logo";

const NAV = [
  { label: "How it works", href: "/#how", key: "how" },
  { label: "Security", href: "/#security", key: "security" },
  { label: "CLI docs", href: "/cli-docs", key: "cli" },
];

export function MarketingHeader({ active }: { active?: "home" | "cli" }) {
  return (
    <header className="sc-l-nav">
      <div className="sc-l-wrap sc-l-nav-inner">
        <Link href="/" className="sc-brand sc-l-brand" aria-label="Secria home">
          <Logo size={28} />
          <span className="sc-brand-word">SECRIA</span>
        </Link>

        <nav className="sc-l-nav-links" aria-label="Primary">
          {NAV.map((item) => {
            const isActive = active === item.key;
            return (
              <Link
                key={item.key}
                href={item.href}
                className={isActive ? "is-active" : undefined}
                aria-current={isActive ? "page" : undefined}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="sc-l-nav-actions">
          <span className="sc-l-nav-pill">
            <i className="sc-l-dot" aria-hidden="true" />
            Self-hosted
          </span>
          <Link className="sc-l-nav-signin" href="/login">
            Sign in
          </Link>
          <Link
            className="sc-btn sc-btn--lime sc-btn--small sc-l-nav-cta"
            href="/login"
          >
            Open the vault
            <ArrowRight size={14} />
          </Link>
        </div>
      </div>
    </header>
  );
}
