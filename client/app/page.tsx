import Link from "next/link";

import {
  ArrowRight,
  Check,
  History,
  Layers,
  Lock,
  Shield,
  Terminal,
} from "@/components/Icons";
import { Logo } from "@/components/Logo";

const LEDGER_ROWS = [
  { key: "DATABASE_URL", status: "synced" },
  { key: "STRIPE_SECRET_KEY", status: "sealed" },
  { key: "RESEND_API_KEY", status: "new" },
  { key: "SENTRY_DSN", status: "synced" },
];

const FEATURES = [
  {
    icon: Shield,
    title: "Envelope encryption",
    body: "A master key wraps one key per project. Secret values never leave the API in plaintext unless an authorized reveal asks for them.",
  },
  {
    icon: Layers,
    title: "Project-scoped access",
    body: "Grant people exactly the projects and environments they need. Workspace admins see everything; members see their lane.",
  },
  {
    icon: History,
    title: "Every reveal is audited",
    body: "Create, update, reveal, download, roll back. The log records who, when, where, and which key — never the value.",
  },
  {
    icon: Terminal,
    title: "CLI-native workflow",
    body: "Push a .env, pull it back, diff before you write, or run a command with secrets injected in memory. No stray files.",
  },
];

const FLOW = [
  { n: "01", title: "Workspace", body: "Your team's top-level vault." },
  { n: "02", title: "Project", body: "One application, one key boundary." },
  { n: "03", title: "Environment", body: "Dev, staging, production, and beyond." },
  { n: "04", title: "Secret", body: "Versioned, encrypted, and accounted for." },
];

export default function LandingPage() {
  return (
    <div className="sc-landing">
      <header className="sc-nav">
        <Link href="/" className="sc-brand" aria-label="Secria home">
          <Logo size={32} />
          <span className="sc-brand-word">SECRIA</span>
        </Link>
        <nav className="sc-nav-links" aria-label="Primary">
          <a className="sc-nav-link" href="#how">
            How it works
          </a>
          <a className="sc-nav-link" href="#security">
            Security
          </a>
          <Link className="sc-btn sc-btn--primary sc-btn--small" href="/login">
            Sign in
            <ArrowRight size={15} />
          </Link>
        </nav>
      </header>

      <main>
        <section className="sc-hero">
          <div className="sc-hero-copy">
            <p className="sc-eyebrow">
              <span className="sc-signal-dot" aria-hidden="true" />
              Self-hosted secrets
            </p>
            <h1>
              Ship secrets without <span className="sc-mark">shipping them.</span>
            </h1>
            <p className="sc-lede">
              Secria is the vault your team actually owns. Envelope-encrypted values,
              project-scoped access, version history, and an honest audit trail — all behind
              one FastAPI service and a CLI that fits your terminal.
            </p>
            <div className="sc-actions">
              <Link className="sc-btn sc-btn--primary sc-btn--lg" href="/login">
                Open the vault
                <ArrowRight size={17} />
              </Link>
              <a className="sc-btn sc-btn--ghost sc-btn--lg" href="#how">
                See how it works
              </a>
            </div>
            <dl className="sc-proof">
              <div>
                <dt>AES-256-GCM</dt>
                <dd>envelope encryption</dd>
              </div>
              <div>
                <dt>100%</dt>
                <dd>audited reveals</dd>
              </div>
              <div>
                <dt>.env</dt>
                <dd>push / pull / run</dd>
              </div>
            </dl>
          </div>

          <div className="sc-hero-visual" aria-hidden="true">
            <div className="sc-visual-grid" />
            <div className="sc-ledger">
              <div className="sc-ledger-top">
                <span className="sc-ledger-dots">
                  <i />
                  <i />
                  <i />
                </span>
                <span className="sc-mono">acme-api / production</span>
                <span className="sc-sealed">
                  <Lock size={12} />
                  sealed
                </span>
              </div>
              <div className="sc-ledger-tabs">
                <span>dev</span>
                <span>staging</span>
                <span className="is-active">production</span>
              </div>
              <div className="sc-ledger-rows">
                {LEDGER_ROWS.map((row) => (
                  <div className="sc-ledger-row" key={row.key}>
                    <span className="sc-ledger-key">{row.key}</span>
                    <span className="sc-ledger-value">••••••••••••</span>
                    <span
                      className={`sc-ledger-status${row.status === "new" ? " is-new" : ""}`}
                    >
                      {row.status}
                    </span>
                  </div>
                ))}
              </div>
              <div className="sc-ledger-foot">
                <span>
                  <Check size={13} /> 14 secrets in sync
                </span>
                <span className="sc-mono">v42</span>
              </div>
            </div>

            <div className="sc-float-card sc-float-card--audit">
              <span className="sc-signal-dot" />
              <div>
                <strong>revealed</strong>
                <span>STRIPE_SECRET_KEY · 2m ago</span>
              </div>
            </div>
            <div className="sc-float-card sc-float-card--cli">
              <span className="sc-prompt">$</span>
              <code>secria run --env prod -- npm start</code>
            </div>
          </div>
        </section>

        <section id="how" className="sc-flow">
          <div className="sc-section-head">
            <p className="sc-eyebrow">The shape of the vault</p>
            <h2>Four layers. One clear path.</h2>
            <p>
              No mystery boxes. Every secret has a home, every permission has a scope, and
              every change has a witness.
            </p>
          </div>
          <div className="sc-flow-grid">
            {FLOW.map((step) => (
              <div className="sc-flow-step" key={step.n}>
                <span className="sc-flow-num">{step.n}</span>
                <h3>{step.title}</h3>
                <p>{step.body}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="sc-features">
          <div className="sc-section-head">
            <p className="sc-eyebrow">Built for the way teams ship</p>
            <h2>Small surface. Hard guarantees.</h2>
            <p>
              Secria does one job: keep secret values out of the wrong hands and make the
              right hands faster.
            </p>
          </div>
          <div className="sc-feature-grid">
            {FEATURES.map((feature) => (
              <article className="sc-feature" key={feature.title}>
                <span className="sc-feature-icon">
                  <feature.icon size={20} />
                </span>
                <h3>{feature.title}</h3>
                <p>{feature.body}</p>
              </article>
            ))}
          </div>
        </section>

        <section id="security" className="sc-security">
          <div className="sc-security-panel">
            <p className="sc-eyebrow sc-eyebrow--on-dark">
              <span className="sc-signal-dot" aria-hidden="true" />
              Sealed by default
            </p>
            <h2>Plaintext has one address: the API.</h2>
            <p>
              The web app never decrypts. The database never sees a raw secret. The master
              key lives outside both, and the ciphertext is bound to its exact workspace,
              project, environment, and key.
            </p>
            <ul className="sc-security-list">
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

          <div className="sc-security-copy">
            <p className="sc-eyebrow">The key chain</p>
            <h2>Three locks, one direction.</h2>
            <p>
              A leaked database backup is not a leaked secret. Without the master key, the
              project keys are noise, and without a project key, the values are noise.
            </p>
            <div className="sc-keychain">
              <div className="sc-keychain-row">
                <span>Master key</span>
                <code>KEK · env only</code>
              </div>
              <div className="sc-keychain-arrow">wraps</div>
              <div className="sc-keychain-row">
                <span>Project key</span>
                <code>DEK · one per project</code>
              </div>
              <div className="sc-keychain-arrow">encrypts</div>
              <div className="sc-keychain-row">
                <span>Secret value</span>
                <code>AES-256-GCM</code>
              </div>
            </div>
          </div>
        </section>

        <section className="sc-cta">
          <div className="sc-cta-inner">
            <div>
              <p className="sc-eyebrow sc-eyebrow--on-dark">Ready when you are</p>
              <h2>Your .env deserves a better home.</h2>
              <p>
                Bring your workspace, your projects, and your team. Secria handles the
                seals, the versions, and the receipts.
              </p>
            </div>
            <Link className="sc-btn sc-btn--lime sc-btn--lg" href="/login">
              Open the vault
              <ArrowRight size={17} />
            </Link>
          </div>
        </section>
      </main>

      <footer className="sc-footer">
        <div className="sc-footer-inner">
          <Link href="/" className="sc-brand sc-brand--small">
            <Logo size={26} />
            <span className="sc-brand-word">SECRIA</span>
          </Link>
          <p className="sc-mono">Secrets, sealed and accounted for.</p>
          <nav className="sc-footer-links" aria-label="Footer">
            <a href="#how">How it works</a>
            <a href="#security">Security</a>
            <Link href="/login">Sign in</Link>
          </nav>
        </div>
      </footer>
    </div>
  );
}
