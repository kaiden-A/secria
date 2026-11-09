import Link from "next/link";

import { Logo } from "@/components/Logo";

const COLUMNS = [
  {
    title: "Product",
    links: [
      { label: "How it works", href: "/#how" },
      { label: "Security", href: "/#security" },
      { label: "CLI docs", href: "/cli-docs" },
    ],
  },
  {
    title: "Source",
    links: [
      {
        label: "GitHub",
        href: "https://github.com/kaiden-A/secria",
        external: true,
      },
      {
        label: "API docs",
        href: "https://github.com/kaiden-A/secria/blob/main/docs/api.md",
        external: true,
      },
      {
        label: "Deploy",
        href: "https://github.com/kaiden-A/secria#setup",
        external: true,
      },
    ],
  },
  {
    title: "Access",
    links: [
      { label: "Sign in", href: "/login" },
      { label: "Open the vault", href: "/login" },
      { label: "Security model", href: "/#security" },
    ],
  },
];

export function MarketingFooter() {
  return (
    <footer className="sc-l-footer">
      <div className="sc-l-wrap">
        <div className="sc-l-footer-grid">
          <div className="sc-l-footer-brand">
            <Link href="/" className="sc-brand sc-l-brand" aria-label="Secria home">
              <Logo size={26} />
              <span className="sc-brand-word">SECRIA</span>
            </Link>
            <p>Secrets, sealed and accounted for.</p>
            <span className="sc-l-footer-note">Self-hosted / your keys</span>
          </div>

          {COLUMNS.map((column) => (
            <div className="sc-l-footer-column" key={column.title}>
              <h2>{column.title}</h2>
              <ul>
                {column.links.map((link) =>
                  "external" in link && link.external ? (
                    <li key={link.label}>
                      <a href={link.href} target="_blank" rel="noreferrer">
                        {link.label}
                      </a>
                    </li>
                  ) : (
                    <li key={link.label}>
                      <Link href={link.href}>{link.label}</Link>
                    </li>
                  ),
                )}
              </ul>
            </div>
          ))}
        </div>

        <div className="sc-l-footer-bottom">
          <span>© 2026 Secria</span>
          <span>Secure ledger / rev. 01</span>
          <span className="sc-l-footer-status">
            <i className="sc-l-dot" aria-hidden="true" />
            Self-hosted
          </span>
        </div>
      </div>
    </footer>
  );
}
