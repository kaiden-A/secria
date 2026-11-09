import type { Metadata, Viewport } from "next";
import Link from "next/link";

import {
  ArrowDown,
  ArrowRight,
  Check,
  Lock,
} from "@/components/Icons";
import { Logo } from "@/components/Logo";
import { CipherDemo } from "@/components/landing/CipherDemo";
import { CopyCommand } from "@/components/landing/CopyCommand";
import { HeroStage } from "@/components/landing/HeroStage";
import { MarketingFooter } from "@/components/site/MarketingFooter";
import { MarketingHeader } from "@/components/site/MarketingHeader";

const PROOF = [
  { value: "AES-256-GCM", label: "Envelope encryption" },
  { value: "100%", label: "Audited reveals" },
  { value: "Self-hosted", label: "Your keys, your database" },
  { value: ".env", label: "Push, pull, run" },
];

const VAULT_LAYERS = [
  {
    number: "01",
    title: "Workspace",
    body: "Your team’s top-level vault.",
    tag: "Top level",
  },
  {
    number: "02",
    title: "Project",
    body: "One application, one key boundary.",
    tag: "Key boundary",
  },
  {
    number: "03",
    title: "Environment",
    body: "Dev, staging, production, and beyond.",
    tag: "Scoped",
  },
  {
    number: "04",
    title: "Secret",
    body: "Versioned, encrypted, and accounted for.",
    tag: "Versioned",
  },
];

const INJECTED = ["DATABASE_URL", "STRIPE_SECRET_KEY", "RESEND_API_KEY"];

const AUDIT_ROWS = [
  { action: "reveal", key: "STRIPE_SECRET_KEY", actor: "you / 2m", tone: "lime" },
  { action: "update", key: "DATABASE_URL", actor: "mia / 1h", tone: "ice" },
  { action: "download", key: ".env / prod", actor: "ci / 3h", tone: "muted" },
];

const ACCESS_ROWS = [
  { role: "admin", access: [true, true, true] },
  { role: "editor", access: [true, true, false] },
  { role: "viewer", access: [true, false, false] },
];

export const metadata: Metadata = {
  title: "Secrets in focus",
  description:
    "Secria is a self-hosted secrets manager with envelope encryption, project-scoped access, audited reveals, and a CLI-native workflow.",
  openGraph: {
    type: "website",
    siteName: "Secria",
    title: "Secria / Secrets in focus",
    description:
      "Envelope-encrypted values, project-scoped access, and an audit trail that records the action, never the value.",
  },
};

export const viewport: Viewport = {
  colorScheme: "dark",
  themeColor: "#061d24",
};

export default function LandingPage() {
  return (
    <div className="sc-landing">
      <a className="sc-l-skip" href="#main">
        Skip to content
      </a>

      <MarketingHeader active="home" />

      <main id="main">
        <section className="sc-l-hero" aria-labelledby="hero-title">
          <div className="sc-l-wrap">
            <h1 id="hero-title" className="sc-l-hero-title">
              Secrets in focus.
            </h1>
            <p className="sc-l-hero-lede">
              Envelope-encrypted values, project-scoped access, and an audit trail
              that records the action, never the value. Self-hosted, CLI-native, and
              yours.
            </p>

            <HeroStage />

            <div className="sc-l-actions sc-l-hero-actions">
              <Link className="sc-btn sc-btn--lime sc-btn--lg" href="/login">
                Open the vault
                <ArrowRight size={17} />
              </Link>
              <a className="sc-btn sc-btn--lg sc-l-btn-ghost" href="#security">
                See the encryption
                <ArrowDown size={16} />
              </a>
            </div>

            <div className="sc-l-hero-foot">
              <span>(01) / Self-hosted secrets</span>
              <span>Fig. 01 / Envelope encryption</span>
              <a href="#how">
                Scroll
                <ArrowDown size={13} />
              </a>
            </div>
          </div>
        </section>

        <section className="sc-l-proof" aria-label="Security guarantees">
          <div className="sc-l-wrap sc-l-proof-inner">
            {PROOF.map((item) => (
              <div className="sc-l-proof-item" key={item.value}>
                <span className="sc-l-proof-value">{item.value}</span>
                <span className="sc-l-proof-label">{item.label}</span>
              </div>
            ))}
          </div>
        </section>

        <section id="how" className="sc-l-paper">
          <div className="sc-l-wrap">
            <div className="sc-l-split-head">
              <h2>Four layers. One key path.</h2>
              <p>
                No mystery boxes. Every secret has a home, every permission has a
                scope, and every change has a witness.
              </p>
            </div>

            <ol className="sc-l-vault">
              {VAULT_LAYERS.map((layer) => (
                <li className="sc-l-vault-row" key={layer.number}>
                  <span className="sc-l-vault-number">{layer.number}</span>
                  <div className="sc-l-vault-copy">
                    <h3>{layer.title}</h3>
                    <p>{layer.body}</p>
                  </div>
                  <span className="sc-l-vault-tag">{layer.tag}</span>
                </li>
              ))}
            </ol>

            <div className="sc-l-section-foot">
              <span>Fig. 02 / Vault model</span>
              <span>Every secret inherits one path. No orphans.</span>
            </div>
          </div>
        </section>

        <section id="product" className="sc-l-product">
          <div className="sc-l-wrap">
            <div className="sc-l-split-head">
              <h2>Small surface. Hard guarantees.</h2>
              <p>
                The product is deliberately narrow. The guarantees are not.
              </p>
            </div>

            <div className="sc-l-bento">
              <article className="sc-l-artifact sc-l-cli" id="cli">
                <div className="sc-l-artifact-bar">
                  <span className="sc-l-window-dots" aria-hidden="true">
                    <i />
                    <i />
                    <i />
                  </span>
                  <span className="sc-l-artifact-name">secria / zsh</span>
                  <span className="sc-l-tag">Sample session</span>
                  <CopyCommand command="secria run --env prod -- npm start" />
                </div>

                <div className="sc-l-terminal" translate="no">
                  <p className="sc-l-term-line">
                    <span className="sc-l-term-prompt">$</span> secria run --env
                    prod -- npm start
                  </p>
                  <p className="sc-l-term-out">
                    <Check size={13} />
                    14 secrets injected
                  </p>
                  <p className="sc-l-term-out">
                    <Check size={13} />
                    0 files written to disk
                  </p>
                  <p className="sc-l-term-out sc-l-term-out--lime">
                    <ArrowRight size={13} />
                    local: http://localhost:3000
                  </p>

                  <div className="sc-l-term-diff">
                    <p className="sc-l-term-line">
                      <span className="sc-l-term-prompt">$</span> secria diff --env
                      prod
                    </p>
                    <p className="sc-l-term-out sc-l-term-out--muted">
                      <span className="sc-l-term-mark">~</span>
                      3 values changed
                    </p>
                    <p className="sc-l-term-out sc-l-term-out--muted">
                      <span className="sc-l-term-mark">+</span>
                      1 new key
                    </p>
                    <p className="sc-l-term-cursor" aria-hidden="true">
                      <span />
                    </p>
                  </div>
                </div>

                <div className="sc-l-injected">
                  <span className="sc-l-injected-label">Injected</span>
                  <ul>
                    {INJECTED.map((key) => (
                      <li key={key}>
                        <Lock size={11} />
                        {key}
                      </li>
                    ))}
                  </ul>
                </div>
              </article>

              <article className="sc-l-artifact sc-l-audit">
                <header className="sc-l-artifact-head">
                  <h3>Audit log</h3>
                  <span className="sc-l-tag">Sample</span>
                </header>

                <div className="sc-l-audit-table">
                  <div className="sc-l-audit-row sc-l-audit-row--head">
                    <span>Action</span>
                    <span>Key</span>
                    <span>Who</span>
                  </div>
                  {AUDIT_ROWS.map((row) => (
                    <div className="sc-l-audit-row" key={`${row.action}-${row.key}`}>
                      <span className={`sc-l-action is-${row.tone}`}>
                        {row.action}
                      </span>
                      <code translate="no">{row.key}</code>
                      <span>{row.actor}</span>
                    </div>
                  ))}
                </div>

                <footer className="sc-l-artifact-foot">
                  <span>
                    <Lock size={12} />
                    Values never logged
                  </span>
                  <span>v42 / 18 versions</span>
                </footer>
              </article>

              <article className="sc-l-artifact sc-l-access">
                <header className="sc-l-artifact-head">
                  <h3>Project access</h3>
                  <span className="sc-l-tag">Sample</span>
                </header>

                <table
                  className="sc-l-access-table"
                  aria-label="Project access by role and environment"
                >
                  <thead>
                    <tr>
                      <th scope="col">Role</th>
                      <th scope="col">dev</th>
                      <th scope="col">stg</th>
                      <th scope="col">prod</th>
                    </tr>
                  </thead>
                  <tbody>
                    {ACCESS_ROWS.map((row) => (
                      <tr key={row.role}>
                        <th scope="row">{row.role}</th>
                        {row.access.map((allowed, index) => (
                          <td key={`${row.role}-${index}`}>
                            <span
                              className={`sc-l-cell${allowed ? " is-on" : ""}`}
                              aria-hidden="true"
                            />
                            <span className="sc-sr-only">
                              {allowed ? "Allowed" : "Not allowed"}
                            </span>
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>

                <footer className="sc-l-artifact-foot">
                  <span>Project-scoped</span>
                  <span>Environment-aware</span>
                </footer>
              </article>
            </div>

            <div className="sc-l-cli-handoff">
              <div>
                <h3>The same vault, in your terminal.</h3>
                <p>
                  Install the CLI, sign in, then push, pull, or diff. Run any
                  command with secrets injected in memory, so no .env is written to
                  disk.
                </p>
                <Link className="sc-l-inline-link" href="/cli-docs">
                  Read the full CLI guide
                  <ArrowRight size={13} />
                </Link>
              </div>
              <div className="sc-l-cli-install">
                <div className="sc-l-cli-install-row">
                  <span className="sc-l-cli-install-label">Install</span>
                  <code translate="no">uv tool install secria</code>
                  <CopyCommand command="uv tool install secria" />
                </div>
                <div className="sc-l-cli-install-row sc-l-cli-install-row--sub">
                  <span className="sc-l-cli-install-label">One-off</span>
                  <code translate="no">uvx secria</code>
                </div>
                <div className="sc-l-cli-install-row sc-l-cli-install-row--sub">
                  <span className="sc-l-cli-install-label">Start</span>
                  <code translate="no">secria login</code>
                </div>
              </div>
            </div>

            <div className="sc-l-section-foot">
              <span>Fig. 03 / Product surface</span>
              <span>No dashboard theatre. Every screen does one job.</span>
            </div>
          </div>
        </section>

        <section id="security" className="sc-l-security">
          <div className="sc-l-wrap">
            <div className="sc-l-split-head">
              <h2>Plaintext has one address.</h2>
              <p>
                The web app never decrypts. The database never sees a raw value. The
                master key lives outside both, and every ciphertext is bound to its
                workspace, project, environment, and key.
              </p>
            </div>

            <div className="sc-l-security-grid">
              <div className="sc-l-security-left">
                <div className="sc-l-keychain" aria-label="Key hierarchy">
                  <div className="sc-l-key-row">
                    <span className="sc-l-key-index">01</span>
                    <div>
                      <strong>Master key</strong>
                      <span>KEK / environment only</span>
                    </div>
                    <code translate="no">SECRIA_MASTER_KEY</code>
                  </div>
                  <div className="sc-l-key-link" aria-hidden="true">
                    <span>wraps</span>
                  </div>
                  <div className="sc-l-key-row">
                    <span className="sc-l-key-index">02</span>
                    <div>
                      <strong>Project key</strong>
                      <span>DEK / one per project</span>
                    </div>
                    <code translate="no">projects.encrypted_dek</code>
                  </div>
                  <div className="sc-l-key-link" aria-hidden="true">
                    <span>encrypts</span>
                  </div>
                  <div className="sc-l-key-row">
                    <span className="sc-l-key-index">03</span>
                    <div>
                      <strong>Secret value</strong>
                      <span>AES-256-GCM / nonce per version</span>
                    </div>
                    <code translate="no">secrets.ciphertext</code>
                  </div>
                </div>

                <ul className="sc-l-bullets">
                  <li>
                    <Check size={16} />
                    AES-256-GCM with a fresh nonce per version
                  </li>
                  <li>
                    <Check size={16} />
                    Project keys wrapped by the master key
                  </li>
                  <li>
                    <Check size={16} />
                    Reveal and download always audited
                  </li>
                </ul>
              </div>

              <CipherDemo />
            </div>

            <div className="sc-l-section-foot">
              <span>Fig. 04 / Key chain</span>
              <span>Plaintext never touches the browser.</span>
            </div>
          </div>
        </section>

        <section className="sc-l-cta">
          <div className="sc-l-wrap sc-l-cta-inner">
            <div className="sc-l-cta-copy">
              <h2>Your .env deserves a better home.</h2>
              <p>
                Bring your workspace, your projects, and your team. Secria handles
                the seals, the versions, and the receipts.
              </p>
              <div className="sc-l-actions">
                <Link className="sc-btn sc-btn--lime sc-btn--lg" href="/login">
                  Open the vault
                  <ArrowRight size={17} />
                </Link>
                <a className="sc-btn sc-btn--lg sc-l-btn-ghost" href="#security">
                  Read the security model
                </a>
              </div>
            </div>

            <div className="sc-l-stamp" aria-hidden="true">
              <svg className="sc-l-stamp-ring" viewBox="0 0 260 260">
                <defs>
                  <path
                    id="sc-l-stamp-path"
                    d="M130,130 m-98,0 a98,98 0 1,1 196,0 a98,98 0 1,1 -196,0"
                  />
                </defs>
                <circle
                  cx="130"
                  cy="130"
                  r="126"
                  fill="none"
                  stroke="currentColor"
                  strokeOpacity="0.58"
                />
                <circle
                  cx="130"
                  cy="130"
                  r="90"
                  fill="none"
                  stroke="currentColor"
                  strokeOpacity="0.42"
                  strokeDasharray="2 7"
                />
                <text className="sc-l-stamp-text">
                  <textPath href="#sc-l-stamp-path" startOffset="0">
                    SECRIA / SEALED / AUDITED / SELF-HOSTED / SECURE LEDGER /
                  </textPath>
                </text>
              </svg>
              <span className="sc-l-stamp-mark">
                <Logo size={54} />
              </span>
            </div>
          </div>

          <div className="sc-l-wrap">
            <div className="sc-l-section-foot">
              <span>Fig. 05 / The seal</span>
              <span>Self-hosted / your keys / no lock-in</span>
            </div>
          </div>
        </section>
      </main>

      <MarketingFooter />
    </div>
  );
}
