import type { ReactNode } from "react";
import Link from "next/link";

import { ArrowRight, Check } from "@/components/Icons";
import { Callout } from "@/components/docs/Callout";
import { CodeBlock } from "@/components/docs/CodeBlock";
import { DocsSidebar } from "@/components/docs/DocsSidebar";
import { InlineCode } from "@/components/docs/InlineCode";
import { CopyCommand } from "@/components/landing/CopyCommand";
import { MarketingFooter } from "@/components/site/MarketingFooter";
import { MarketingHeader } from "@/components/site/MarketingHeader";
import {
  COMMAND_GROUPS,
  FAQ,
  RECIPES,
  TROUBLESHOOTING,
} from "@/lib/cli-docs";

function SectionHeading({
  eyebrow,
  title,
  id,
  children,
}: {
  eyebrow: string;
  title: string;
  id: string;
  children?: ReactNode;
}) {
  return (
    <>
      <p className="sc-docs-eyebrow">{eyebrow}</p>
      <h2 id={id}>{title}</h2>
      {children ? <div className="sc-docs-section-lede">{children}</div> : null}
    </>
  );
}

export function CliDocs() {
  return (
    <div className="sc-landing sc-docs">
      <a className="sc-l-skip" href="#main">
        Skip to content
      </a>

      <MarketingHeader active="cli" />

      <main id="main">
        <section className="sc-docs-hero">
          <div className="sc-l-wrap sc-docs-hero-grid">
            <div className="sc-docs-hero-copy">
              <p className="sc-docs-kicker">Secria CLI / field guide</p>
              <h1 className="sc-docs-title">Your vault, in the terminal.</h1>
              <p className="sc-docs-lede">
                Install it once, link a folder, and stop passing{" "}
                <code>.env</code> files around. This guide teaches the CLI
                through a real project, then gives you the full command
                reference. No flag memorization required.
              </p>

              <div className="sc-docs-install">
                <span className="sc-docs-install-label">Install</span>
                <code translate="no">uv tool install secria</code>
                <CopyCommand command="uv tool install secria" />
              </div>

              <div className="sc-docs-hero-actions">
                <a className="sc-btn sc-btn--lime sc-btn--lg" href="#scenario">
                  Start the scenario
                  <ArrowRight size={17} />
                </a>
                <a
                  className="sc-btn sc-btn--lg sc-l-btn-ghost"
                  href="#commands"
                >
                  Command reference
                </a>
              </div>

              <div className="sc-docs-meta">
                <span>Python 3.12+</span>
                <span>Windows / macOS / Linux</span>
                <span>CLI 0.1.0</span>
              </div>
            </div>

            <div className="sc-docs-hero-card">
              <div className="sc-docs-hero-card-bar">
                <span className="sc-l-window-dots" aria-hidden="true">
                  <i />
                  <i />
                  <i />
                </span>
                <span>secria / first run</span>
                <span className="sc-l-tag">sample</span>
              </div>
              <div className="sc-l-terminal" translate="no">
                <p className="sc-l-term-line">
                  <span className="sc-l-term-prompt">$</span> secria login
                </p>
                <p className="sc-l-term-out sc-l-term-out--muted">
                  Signed in as you@example.com
                </p>
                <p className="sc-l-term-line">
                  <span className="sc-l-term-prompt">$</span> secria init
                  --workspace elysiaa --project mits-warden-system --env dev
                </p>
                <p className="sc-l-term-out sc-l-term-out--muted">
                  Linked .secria.yaml → elysiaa/mits-warden-system/dev
                </p>
                <p className="sc-l-term-line">
                  <span className="sc-l-term-prompt">$</span> secria push
                </p>
                <p className="sc-l-term-out">
                  <Check size={13} /> +3 added · ~1 changed · =12 unchanged
                </p>
                <p className="sc-l-term-line">
                  <span className="sc-l-term-prompt">$</span> secria run --env
                  prod -- npm start
                </p>
                <p className="sc-l-term-out sc-l-term-out--lime">
                  <ArrowRight size={13} /> 14 secrets injected · 0 files written
                </p>
              </div>
            </div>
          </div>
        </section>

        <div className="sc-l-wrap sc-docs-shell">
          <DocsSidebar />

          <article className="sc-docs-article">
            <section
              id="quick-start"
              className="sc-docs-section"
              aria-labelledby="quick-start-title"
            >
              <SectionHeading
                eyebrow="01 / Quick start"
                title="Five steps, one folder."
                id="quick-start-title"
              >
                <p>
                  You do not need to learn every command first. Get one folder
                  connected, push one file, and run one process. Everything else
                  is a variation on that loop.
                </p>
              </SectionHeading>

              <ol className="sc-docs-steps">
                <li className="sc-docs-step">
                  <h3>Install the CLI</h3>
                  <p>
                    Python 3.12 or newer is required. Use{" "}
                    <InlineCode text="uv tool install secria" /> for a permanent
                    install, or <InlineCode text="uvx secria" /> for a one-off
                    run.
                  </p>
                  <CodeBlock
                    title="install"
                    code={`uv tool install secria

# or with pipx
pipx install secria

# run once without installing
uvx secria --help`}
                  />
                </li>

                <li className="sc-docs-step">
                  <h3>Sign in</h3>
                  <p>
                    <InlineCode text="secria login" /> opens the Zitadel device
                    flow in your browser. Approve the code and the session is
                    stored in your OS keychain.
                  </p>
                  <CodeBlock
                    title="sign in"
                    code={`secria login

# self-hosted instance
secria login --server https://secria.example.com

# browser did not open?
secria login --no-browser`}
                  />
                </li>

                <li className="sc-docs-step">
                  <h3>Create or find a project</h3>
                  <p>
                    A project lives inside a workspace. Every new project gets{" "}
                    <InlineCode text="dev" />, <InlineCode text="staging" />,
                    and <InlineCode text="prod" /> automatically.
                  </p>
                  <CodeBlock
                    title="create or find a project"
                    code={`secria workspace list
secria project list --workspace elysiaa

# create one in a specific workspace
secria project create mits-warden-system --workspace elysiaa`}
                  />
                  <Callout tone="warn" title="Creating is not linking">
                    <p>
                      <InlineCode text="project create" /> only creates the
                      project. It does not write a link file unless you pass{" "}
                      <InlineCode text="--from-env" />. The next step links this
                      folder.
                    </p>
                  </Callout>
                </li>

                <li className="sc-docs-step">
                  <h3>Link this folder</h3>
                  <p>
                    <InlineCode text="secria init" /> writes a{" "}
                    <InlineCode text=".secria.yaml" /> file in the current
                    directory. That file is how later commands know which
                    project and environment you mean.
                  </p>
                  <CodeBlock
                    title="link this folder"
                    code={`secria init --workspace elysiaa --project mits-warden-system --env dev`}
                  />
                  <p>
                    Pass all three flags when you want a deterministic link. If
                    you omit them, the CLI can inherit values from a parent
                    link file or your default workspace.
                  </p>
                </li>

                <li className="sc-docs-step">
                  <h3>Push, then run</h3>
                  <p>
                    <InlineCode text="diff" /> is read-only.{" "}
                    <InlineCode text="push" /> uploads after a confirmation.{" "}
                    <InlineCode text="run" /> injects secrets in memory without
                    writing a file.
                  </p>
                  <CodeBlock
                    title="first push and run"
                    code={`secria diff
secria push
secria run --env dev -- npm start`}
                  />
                </li>
              </ol>

              <h3>What success looks like</h3>
              <p>
                Your link file should name the workspace, project, and
                environment you intended:
              </p>
              <CodeBlock
                title=".secria.yaml"
                copyable={false}
                code={`# Secria link file. Safe to commit: it contains no secrets.
workspace: elysiaa
project: mits-warden-system
environment: dev
server: https://secria.example.com`}
              />
              <p>
                Confirm it from the terminal with{" "}
                <InlineCode text="secria doctor --offline" />. The{" "}
                <InlineCode text="Link file" /> row prints the resolved path.
              </p>
              <CodeBlock
                title="verify the link"
                code={`# macOS / Linux
cat .secria.yaml

# Windows PowerShell
Get-Content .secria.yaml

secria doctor --offline`}
              />

              <Callout tone="tip" title="Why does a fresh project show Envs = 3?">
                <p>
                  That is expected. Every project is created with{" "}
                  <InlineCode text="dev" />, <InlineCode text="staging" />, and{" "}
                  <InlineCode text="prod" />. The Envs column counts
                  environments, not secrets. A new project can have three empty
                  environments and zero secrets.
                </p>
              </Callout>
            </section>

            <section
              id="mental-model"
              className="sc-docs-section"
              aria-labelledby="mental-model-title"
            >
              <SectionHeading
                eyebrow="02 / Mental model"
                title="One path, resolved for you."
                id="mental-model-title"
              >
                <p>
                  Every command operates on one path:{" "}
                  <InlineCode text="workspace / project / environment / key" />.
                  The flags exist only to answer “which path?”.
                </p>
              </SectionHeading>

              <div className="sc-docs-layers" aria-label="Vault hierarchy">
                <div className="sc-docs-layer">
                  <span>01</span>
                  <strong>Workspace</strong>
                  <small>Your team’s top-level vault.</small>
                </div>
                <div className="sc-docs-layer">
                  <span>02</span>
                  <strong>Project</strong>
                  <small>One application, one key boundary.</small>
                </div>
                <div className="sc-docs-layer">
                  <span>03</span>
                  <strong>Environment</strong>
                  <small>Dev, staging, prod, and beyond.</small>
                </div>
                <div className="sc-docs-layer">
                  <span>04</span>
                  <strong>Secret</strong>
                  <small>A versioned key and value.</small>
                </div>
              </div>

              <h3>How the CLI finds the path</h3>
              <div className="sc-docs-table-wrap">
                <table className="sc-docs-table">
                  <thead>
                    <tr>
                      <th>Level</th>
                      <th>Flag</th>
                      <th>Fallback order</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>Workspace</td>
                      <td>
                        <code>--workspace</code>
                      </td>
                      <td>
                        Existing <code>.secria.yaml</code> → default workspace
                        from <code>workspace use</code> → prompt or error
                      </td>
                    </tr>
                    <tr>
                      <td>Project</td>
                      <td>
                        <code>--project</code>
                      </td>
                      <td>
                        Existing <code>.secria.yaml</code> → the only project
                        in the workspace → prompt
                      </td>
                    </tr>
                    <tr>
                      <td>Environment</td>
                      <td>
                        <code>--env</code>
                      </td>
                      <td>
                        Existing <code>.secria.yaml</code> →{" "}
                        <code>dev</code> → the only environment → prompt
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <Callout tone="warn" title="A stale link file beats your default workspace">
                <p>
                  If a <InlineCode text=".secria.yaml" /> in this folder or a
                  parent says <InlineCode text="project: aura" />, then{" "}
                  <InlineCode text="secria init" /> will keep that project even
                  after you run <InlineCode text="workspace use elysiaa" />. Pass{" "}
                  <InlineCode text="--project" /> (and usually{" "}
                  <InlineCode text="--workspace" />) when you need to be sure.
                </p>
              </Callout>

              <h3>The two “env” words</h3>
              <div className="sc-docs-split">
                <div className="sc-docs-card">
                  <span className="sc-docs-card-label">Secria environment</span>
                  <code>--env prod</code>
                  <p>
                    A scope inside a project. It holds versions, policies, and
                    audit history. This is what <InlineCode text="--env" />{" "}
                    selects.
                  </p>
                </div>
                <div className="sc-docs-card">
                  <span className="sc-docs-card-label">Local file</span>
                  <code>.env</code>
                  <p>
                    A file on your disk. It is the positional{" "}
                    <InlineCode text="FILE" /> for{" "}
                    <InlineCode text="push" /> and{" "}
                    <InlineCode text="diff" />, or the{" "}
                    <InlineCode text="--out" /> target for{" "}
                    <InlineCode text="pull" />.
                  </p>
                </div>
              </div>

              <p>
                So <InlineCode text="secria push .env --env prod" /> reads the
                local file <InlineCode text=".env" /> and uploads it to the
                Secria environment named <InlineCode text="prod" />.
              </p>

              <h3>The link file</h3>
              <p>
                <InlineCode text="init" /> writes{" "}
                <InlineCode text=".secria.yaml" /> and the CLI searches for it
                in the current directory and every parent. It contains no
                secrets, so it is safe to commit. A closer file wins, which is
                how a monorepo can link the root and still give one package its
                own project.
              </p>
            </section>

            <section
              id="scenario"
              className="sc-docs-section"
              aria-labelledby="scenario-title"
            >
              <SectionHeading
                eyebrow="03 / Full scenario"
                title="Ship Mits Warden System."
                id="scenario-title"
              >
                <p>
                  A small team has a workspace called{" "}
                  <InlineCode text="elysiaa" />, a repo called{" "}
                  <InlineCode text="mits-warden-system" />, and three
                  environments. Follow the same path they do, from an empty
                  folder to a CI deploy.
                </p>
              </SectionHeading>

              <ol className="sc-docs-steps">
                <li className="sc-docs-step">
                  <h3>Create the project in the right workspace</h3>
                  <p>
                    <InlineCode text="workspace use" /> sets a machine default,
                    but an existing link file still wins. Passing{" "}
                    <InlineCode text="--workspace" /> to{" "}
                    <InlineCode text="project create" /> removes the ambiguity.
                  </p>
                  <CodeBlock
                    title="01 / create in elysiaa"
                    code={`secria workspace use elysiaa
secria project list --workspace elysiaa
secria project create mits-warden-system --workspace elysiaa`}
                  />
                  <p>
                    The project now has <InlineCode text="dev" />,{" "}
                    <InlineCode text="staging" />, and{" "}
                    <InlineCode text="prod" />. They are empty, but they exist.
                  </p>
                </li>

                <li className="sc-docs-step">
                  <h3>Link the repo to that project</h3>
                  <p>
                    This writes the link file at the repo root. Every command
                    run below it now resolves the same path.
                  </p>
                  <CodeBlock
                    title="02 / link the repo"
                    code={`secria init --workspace elysiaa --project mits-warden-system --env dev`}
                  />
                  <CodeBlock
                    title=".secria.yaml"
                    copyable={false}
                    code={`workspace: elysiaa
project: mits-warden-system
environment: dev`}
                  />
                </li>

                <li className="sc-docs-step">
                  <h3>Push the first .env</h3>
                  <p>
                    Start with a local file. The CLI hashes the values locally
                    and sends only the hashes for the comparison, then uploads
                    the values after you confirm.
                  </p>
                  <CodeBlock
                    title=".env (values redacted)"
                    copyable={false}
                    code={`DATABASE_URL=postgres://...
STRIPE_SECRET_KEY=sk_test_...
RESEND_API_KEY=re_...`}
                  />
                  <CodeBlock
                    title="03 / compare, then push"
                    code={`secria diff .env --env dev
secria push .env --env dev`}
                  />
                  <p>
                    The diff table marks added, changed, removed, and unchanged
                    keys. Unchanged values do not create a new version. The
                    default mode is <InlineCode text="merge" />; add{" "}
                    <InlineCode text="--replace" /> only when the remote
                    environment should match the file exactly.
                  </p>
                </li>

                <li className="sc-docs-step">
                  <h3>A teammate clones the repo</h3>
                  <p>
                    Because <InlineCode text=".secria.yaml" /> is committed,
                    the teammate does not need to guess the workspace or
                    project. They sign in and pull.
                  </p>
                  <CodeBlock
                    title="04 / teammate setup"
                    code={`git clone https://github.com/kaiden-A/mits-warden-system.git
cd mits-warden-system
secria login
secria pull --out .env --env dev --force`}
                  />
                  <p>
                    <InlineCode text="pull" /> refuses to overwrite an existing
                    file without <InlineCode text="--force" />, writes with
                    owner-only permissions, and warns if the file is not in{" "}
                    <InlineCode text=".gitignore" />.
                  </p>
                </li>

                <li className="sc-docs-step">
                  <h3>Run without writing a file</h3>
                  <p>
                    <InlineCode text="run" /> is the safest local workflow: it
                    fetches the environment, merges the values into the child
                    process, and executes the command. No <InlineCode text=".env" />{" "}
                    is written to disk.
                  </p>
                  <CodeBlock
                    title="05 / run with secrets in memory"
                    code={`secria run --env dev -- npm run dev`}
                  />
                  <p>
                    Secrets override existing shell variables with the same
                    name. <InlineCode text="SECRIA_TOKEN" /> is removed from the
                    child environment, and the child’s exit code becomes the
                    CLI’s exit code.
                  </p>
                </li>

                <li className="sc-docs-step">
                  <h3>Promote to staging and production</h3>
                  <p>
                    Use separate files for separate environments. Compare
                    first, then push. Avoid pushing a dev file straight to prod.
                  </p>
                  <CodeBlock
                    title="06 / promote"
                    code={`secria diff .env.staging --env staging
secria push .env.staging --env staging

secria diff .env.prod --env prod
secria push .env.prod --env prod`}
                  />
                  <Callout tone="warn" title="Replace is destructive by design">
                    <p>
                      <InlineCode text="push --replace" /> removes remote keys
                      that are missing from the file. It asks for a second
                      confirmation unless you pass{" "}
                      <InlineCode text="-y" />. Use it for a full sync, not for
                      a partial update.
                    </p>
                  </Callout>
                </li>

                <li className="sc-docs-step">
                  <h3>Rotate a secret</h3>
                  <p>
                    One-off updates are fine for rotation. The value gets a new
                    version, and the next read or run uses it.
                  </p>
                  <CodeBlock
                    title="07 / rotate"
                    code={`secria secrets set STRIPE_SECRET_KEY=sk_live_new --env prod
secria run --env prod -- ./deploy.sh`}
                  />
                </li>

                <li className="sc-docs-step">
                  <h3>Wire up CI with a service token</h3>
                  <p>
                    Create a token scoped to one project and environment. Store
                    it as a masked secret in your CI provider. The token is
                    shown once.
                  </p>
                  <CodeBlock
                    title="08 / create a CI token"
                    code={`secria token create --name github-actions --access read --env prod --expires-in-days 90`}
                  />
                  <p>
                    A service token already knows its workspace, project, and
                    environment. Do not pass those flags in CI; the CLI reads
                    the scope from the token.
                  </p>
                  <CodeBlock
                    title=".github/workflows/deploy.yml"
                    code={`name: deploy
on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    env:
      SECRIA_API_URL: https://secria.example.com
      SECRIA_TOKEN: \${{ secrets.SECRIA_TOKEN }}
    steps:
      - uses: actions/checkout@v4
      - run: uvx secria pull --out .env --force
      - run: npm ci
      - run: npm test`}
                  />
                  <p>
                    <InlineCode text="read" /> can list, diff, pull, run, and
                    get. <InlineCode text="read_write" /> can also push, set, and
                    unset. A service token cannot create other tokens or manage
                    members.
                  </p>
                </li>
              </ol>

              <Callout tone="tip" title="What the team gets">
                <p>
                  One source of truth per environment, versions on every change,
                  audited reveals and downloads, and no long-lived plaintext in
                  CI logs. The web app never decrypts; only the API does.
                </p>
              </Callout>
            </section>

            <section
              id="linking"
              className="sc-docs-section"
              aria-labelledby="linking-title"
            >
              <SectionHeading
                eyebrow="04 / Linking"
                title="Pick the project, then prove it."
                id="linking-title"
              >
                <p>
                  Most “wrong project” moments come from one of three commands
                  doing similar-looking things. Here is the difference.
                </p>
              </SectionHeading>

              <div className="sc-docs-table-wrap">
                <table className="sc-docs-table">
                  <thead>
                    <tr>
                      <th>Command</th>
                      <th>Creates project?</th>
                      <th>Pushes file?</th>
                      <th>Writes .secria.yaml?</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>
                        <code>secria project create NAME</code>
                      </td>
                      <td>Yes</td>
                      <td>No</td>
                      <td>No</td>
                    </tr>
                    <tr>
                      <td>
                        <code>
                          secria project create NAME --from-env FILE --env dev
                        </code>
                      </td>
                      <td>Yes</td>
                      <td>Yes</td>
                      <td>Yes</td>
                    </tr>
                    <tr>
                      <td>
                        <code>secria init --workspace ... --project ...</code>
                      </td>
                      <td>No</td>
                      <td>No</td>
                      <td>Yes</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <h3>The deterministic link</h3>
              <CodeBlock
                title="always the same target"
                code={`secria init --workspace elysiaa --project mits-warden-system --env dev`}
              />
              <p>
                Use this form in scripts, onboarding docs, and anywhere a stale
                link file could send you to the wrong project. It overwrites the
                local <InlineCode text=".secria.yaml" />.
              </p>

              <h3>Verify before you push</h3>
              <CodeBlock
                title="check the link"
                code={`# macOS / Linux
cat .secria.yaml

# Windows PowerShell
Get-Content .secria.yaml

secria doctor --offline`}
              />
              <p>
                <InlineCode text="doctor --offline" /> prints the link file and
                the resolved scope without calling the network. Drop{" "}
                <InlineCode text="--offline" /> to also check API health and the
                identity-provider discovery document.
              </p>

              <h3>Switch this folder to another project</h3>
              <p>
                Run <InlineCode text="init" /> again with the new flags. The
                local file is replaced. Commands that already read the old
                values only see the new ones on the next invocation.
              </p>
              <CodeBlock
                title="switch projects"
                code={`secria init --workspace elysiaa --project billing --env dev`}
              />

              <h3>Monorepos</h3>
              <p>
                Put the link file at the repo root. Every package below it
                inherits the same workspace, project, and environment. If one
                package needs its own project, run <InlineCode text="init" />{" "}
                inside that package; the nearest link file wins.
              </p>
              <CodeBlock
                title="monorepo shape"
                code={`repo/
  .secria.yaml          # workspace: elysiaa, project: platform, env: dev
  apps/web/             # inherits the root link
  apps/billing/         # closer .secria.yaml -> project: billing`}
                copyable={false}
              />

              <Callout tone="note" title="Deleting a project is not in the CLI yet">
                <p>
                  The CLI can create and list projects, but it does not expose
                  deletion. Use the web app, or the API’s{" "}
                  <InlineCode text="DELETE /api/v1/projects/{id}" /> endpoint
                  with a workspace owner or admin session.
                </p>
              </Callout>
            </section>

            <section
              id="daily-workflow"
              className="sc-docs-section"
              aria-labelledby="daily-workflow-title"
            >
              <SectionHeading
                eyebrow="05 / Daily workflow"
                title="Push, pull, diff, run."
                id="daily-workflow-title"
              >
                <p>
                  These four commands are the job. The rest of the CLI exists to
                  set them up or inspect what happened.
                </p>
              </SectionHeading>

              <h3 id="push">
                <code>push</code> — upload a file
              </h3>
              <p>
                <InlineCode text="push" /> parses the file locally, hashes each
                value with SHA-256, asks the server for a diff, shows you the
                result, and then uploads the values after confirmation.
              </p>
              <CodeBlock
                title="push"
                code={`secria push                 # reads .env, merges
secria push .env.prod --env prod
secria push .env --env prod --dry-run
secria push .env --env prod --replace -y`}
              />
              <div className="sc-docs-table-wrap">
                <table className="sc-docs-table">
                  <thead>
                    <tr>
                      <th>Diff mark</th>
                      <th>Meaning</th>
                      <th>What happens</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>
                        <code>+</code>
                      </td>
                      <td>Added</td>
                      <td>The key exists locally but not remotely.</td>
                    </tr>
                    <tr>
                      <td>
                        <code>~</code>
                      </td>
                      <td>Changed</td>
                      <td>The value differs; a new version is created.</td>
                    </tr>
                    <tr>
                      <td>
                        <code>-</code>
                      </td>
                      <td>Removed</td>
                      <td>
                        The key exists remotely but not locally. Only{" "}
                        <code>--replace</code> removes it.
                      </td>
                    </tr>
                    <tr>
                      <td>
                        <code>=</code>
                      </td>
                      <td>Unchanged</td>
                      <td>The hash matches; no new version is created.</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <h3 id="pull">
                <code>pull</code> — write a file
              </h3>
              <p>
                <InlineCode text="pull" /> writes the environment to a local
                file. It defaults to <InlineCode text=".env" /> and refuses to
                overwrite unless you pass <InlineCode text="--force" />.
              </p>
              <CodeBlock
                title="pull"
                code={`secria pull --env dev
secria pull --env prod --out .env.prod --force
secria pull --env prod --out secrets.json --format json --force
secria pull --env prod --out secrets.yaml --format yaml --force`}
              />
              <Callout tone="warn" title="Pull writes plaintext to disk">
                <p>
                  The file is created with owner-only permissions, and the CLI
                  warns if it is not in <InlineCode text=".gitignore" />. On a
                  shared machine, prefer <InlineCode text="run" /> or delete the
                  file as soon as the process exits.
                </p>
              </Callout>

              <h3 id="diff">
                <code>diff</code> — compare only
              </h3>
              <p>
                <InlineCode text="diff" /> shows the same table as{" "}
                <InlineCode text="push" /> but never writes. It is the right
                command before a deploy or in a pre-commit check.
              </p>
              <CodeBlock
                title="diff"
                code={`secria diff
secria diff .env.prod --env prod`}
              />

              <h3 id="run">
                <code>run</code> — inject in memory
              </h3>
              <p>
                Everything after <InlineCode text="--" /> is the command to run.
                The CLI fetches the environment, merges the values over your
                current environment variables, and starts the child process.
              </p>
              <CodeBlock
                title="run"
                code={`secria run --env dev -- npm start
secria run --env test -- pytest
secria run --env prod -- ./deploy.sh`}
              />
              <ul className="sc-docs-list">
                <li>Secret values override shell variables with the same name.</li>
                <li>
                  <InlineCode text="SECRIA_TOKEN" /> is removed from the child
                  environment.
                </li>
                <li>The child’s exit code becomes the CLI’s exit code.</li>
                <li>No file is written to disk.</li>
              </ul>

              <h3>One-off secret operations</h3>
              <p>
                Use these for small edits and inspection. For bulk work, push
                and pull are faster and safer.
              </p>
              <CodeBlock
                title="secrets"
                code={`secria secrets list --env dev
secria secrets get DATABASE_URL --env dev
secria secrets set DATABASE_URL=postgres://... --env dev
secria secrets unset OLD_KEY --env dev`}
              />
              <p>
                <InlineCode text="secrets list" /> shows keys and metadata with
                values masked. <InlineCode text="secrets get" /> reveals one
                value and records an audit event.
              </p>
            </section>

            <section
              id="authentication"
              className="sc-docs-section"
              aria-labelledby="authentication-title"
            >
              <SectionHeading
                eyebrow="06 / Authentication"
                title="Two ways in: a person or a token."
                id="authentication-title"
              >
                <p>
                  Your laptop uses a browser session. CI uses a service token.
                  They have different powers and different storage.
                </p>
              </SectionHeading>

              <div className="sc-docs-split">
                <div className="sc-docs-card">
                  <span className="sc-docs-card-label">Human session</span>
                  <h3>Device flow + keychain</h3>
                  <p>
                    <InlineCode text="secria login" /> opens the Zitadel device
                    flow. Tokens live in the OS keychain, scoped per server host.
                    Access tokens refresh automatically.
                  </p>
                  <CodeBlock
                    title="human"
                    code={`secria login
secria whoami
secria logout`}
                  />
                </div>
                <div className="sc-docs-card">
                  <span className="sc-docs-card-label">Machine token</span>
                  <h3>Service token + env var</h3>
                  <p>
                    A service token is scoped to one project and environment. It
                    bypasses the browser and is stored in the CI provider’s
                    secret store.
                  </p>
                  <CodeBlock
                    title="ci"
                    code={`export SECRIA_API_URL=https://secria.example.com
export SECRIA_TOKEN=secria_st_...
secria whoami`}
                  />
                </div>
              </div>

              <h3>Service token access</h3>
              <div className="sc-docs-table-wrap">
                <table className="sc-docs-table">
                  <thead>
                    <tr>
                      <th>Access</th>
                      <th>Can do</th>
                      <th>Cannot do</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>
                        <code>read</code>
                      </td>
                      <td>list, diff, pull, run, get</td>
                      <td>push, set, unset, manage members, create tokens</td>
                    </tr>
                    <tr>
                      <td>
                        <code>read_write</code>
                      </td>
                      <td>everything read can do, plus push, set, unset</td>
                      <td>manage members, create tokens, change workspace roles</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <p>
                With a service token, do not pass{" "}
                <InlineCode text="--workspace" />,{" "}
                <InlineCode text="--project" />, or{" "}
                <InlineCode text="--env" />. The token has exactly one scope, and
                the CLI reads it from{" "}
                <InlineCode text="/api/v1/service-tokens/current" />. A flag that
                does not match produces a scope error.
              </p>
              <CodeBlock
                title="service-token mode"
                code={`# no workspace/project/env flags are needed
secria pull --out .env --force
secria run -- npm test
secria whoami

# whoami prints the token name, access, and scope`}
              />

              <h3>Check the machine</h3>
              <CodeBlock
                title="doctor"
                code={`secria doctor
secria doctor --offline`}
              />
              <p>
                <InlineCode text="doctor" /> prints the CLI version, config
                directory, resolved server and IdP, keyring backend, session
                state, link file, API health, and discovery document. It never
                prints tokens.
              </p>

              <Callout tone="note" title="The CLI never holds the master key">
                <p>
                  The API decrypts for authorized responses. The CLI receives
                  values for pull, run, get, and download, but it never stores
                  the server master key or project data keys. Logs and audit
                  events contain key names and counts, never values.
                </p>
              </Callout>
            </section>

            <section
              id="configuration"
              className="sc-docs-section"
              aria-labelledby="configuration-title"
            >
              <SectionHeading
                eyebrow="07 / Configuration"
                title="Flags beat env vars. Env vars beat files."
                id="configuration-title"
              >
                <p>
                  The CLI resolves one value from several places. When in doubt,
                  ask it where the value came from.
                </p>
              </SectionHeading>

              <h3>Server URL precedence</h3>
              <div className="sc-docs-table-wrap">
                <table className="sc-docs-table">
                  <thead>
                    <tr>
                      <th>Order</th>
                      <th>Source</th>
                      <th>Example</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>1</td>
                      <td>
                        <code>--server</code> on <code>login</code>
                      </td>
                      <td>
                        <code>secria login --server https://secria.example.com</code>
                      </td>
                    </tr>
                    <tr>
                      <td>2</td>
                      <td>
                        <code>SECRIA_API_URL</code>
                      </td>
                      <td>
                        <code>SECRIA_API_URL=https://secria.example.com</code>
                      </td>
                    </tr>
                    <tr>
                      <td>3</td>
                      <td>Saved config</td>
                      <td>
                        <code>secria config set api-url ...</code>
                      </td>
                    </tr>
                    <tr>
                      <td>4</td>
                      <td>
                        <code>.secria.yaml</code> <code>server:</code>
                      </td>
                      <td>A committed link file for teammates</td>
                    </tr>
                    <tr>
                      <td>5</td>
                      <td>Built-in default</td>
                      <td>The hosted Secria API</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <h3>Config files</h3>
              <div className="sc-docs-table-wrap">
                <table className="sc-docs-table">
                  <thead>
                    <tr>
                      <th>Platform</th>
                      <th>Path</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>Windows</td>
                      <td>
                        <code>%LOCALAPPDATA%\secria\config.json</code>
                      </td>
                    </tr>
                    <tr>
                      <td>macOS</td>
                      <td>
                        <code>~/Library/Application Support/secria/config.json</code>
                      </td>
                    </tr>
                    <tr>
                      <td>Linux</td>
                      <td>
                        <code>~/.config/secria/config.json</code>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <CodeBlock
                title="config"
                code={`secria config show
secria config set api-url https://secria.example.com
secria config set zitadel-issuer https://auth.example.com
secria config set zitadel-client-id 123456789
secria config path`}
              />
              <p>
                <InlineCode text="config show" /> includes a{" "}
                <InlineCode text="Source" /> column so you can see whether a
                value came from the environment, saved config, the link file, or
                the default.
              </p>

              <h3>Environment variables</h3>
              <div className="sc-docs-table-wrap">
                <table className="sc-docs-table">
                  <thead>
                    <tr>
                      <th>Variable</th>
                      <th>Purpose</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>
                        <code>SECRIA_API_URL</code>
                      </td>
                      <td>Override the server URL for one shell or CI job.</td>
                    </tr>
                    <tr>
                      <td>
                        <code>SECRIA_TOKEN</code>
                      </td>
                      <td>
                        Authenticate with a service token instead of a browser
                        session.
                      </td>
                    </tr>
                    <tr>
                      <td>
                        <code>SECRIA_CONFIG_DIR</code>
                      </td>
                      <td>Move config.json and fallback credentials.</td>
                    </tr>
                    <tr>
                      <td>
                        <code>SECRIA_DISABLE_KEYRING=1</code>
                      </td>
                      <td>
                        Force the mode <code>0600</code> file fallback instead of
                        the OS keychain.
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <Callout tone="warn" title="Installed builds ignore project .env auth settings">
                <p>
                  A repository must not be able to redirect your login to another
                  server. An installed CLI ignores a project’s{" "}
                  <InlineCode text=".env" /> for{" "}
                  <InlineCode text="SECRIA_API_URL" /> and the Zitadel values. A
                  source checkout reads only the allowed CLI keys for local
                  development.
                </p>
              </Callout>

              <h3>Self-hosted setup</h3>
              <CodeBlock
                title="self-hosted"
                code={`secria login --server https://secria.example.com

# later commands need no --server
secria doctor
secria workspace list`}
              />
              <p>
                The CLI reads the public{" "}
                <InlineCode text="/api/v1/config" /> endpoint to discover the
                Zitadel issuer and client ID, so you do not type those values
                yourself.
              </p>
            </section>

            <section
              id="commands"
              className="sc-docs-section"
              aria-labelledby="commands-title"
            >
              <SectionHeading
                eyebrow="08 / Reference"
                title="Every command, grouped."
                id="commands-title"
              >
                <p>
                  This is the map. Each command also supports{" "}
                  <InlineCode text="secria <command> --help" /> in your
                  terminal.
                </p>
              </SectionHeading>

              {COMMAND_GROUPS.map((group) => (
                <section
                  className="sc-docs-cmd-group"
                  key={group.id}
                  aria-labelledby={`cmd-${group.id}`}
                >
                  <h3 id={`cmd-${group.id}`}>{group.title}</h3>
                  <p>{group.blurb}</p>
                  <div className="sc-docs-table-wrap">
                    <table className="sc-docs-table">
                      <thead>
                        <tr>
                          <th>Command</th>
                          <th>What it does</th>
                          <th>Flags</th>
                          <th>Example</th>
                        </tr>
                      </thead>
                      <tbody>
                        {group.rows.map((row) => (
                          <tr key={row.command}>
                            <td>
                              <code>{row.command}</code>
                            </td>
                            <td>{row.purpose}</td>
                            <td>
                              {row.flags.length > 0 ? (
                                <div className="sc-docs-flag-list">
                                  {row.flags.map((flag) => (
                                    <code key={flag}>{flag}</code>
                                  ))}
                                </div>
                              ) : (
                                <span className="sc-docs-muted">—</span>
                              )}
                            </td>
                            <td>
                              <code>{row.example}</code>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </section>
              ))}

              <h3 id="exit-codes">Exit codes</h3>
              <div className="sc-docs-table-wrap">
                <table className="sc-docs-table">
                  <thead>
                    <tr>
                      <th>Code</th>
                      <th>Meaning</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>
                        <code>0</code>
                      </td>
                      <td>Success.</td>
                    </tr>
                    <tr>
                      <td>
                        <code>1</code>
                      </td>
                      <td>
                        A CLI, API, auth, or file error. The message is printed to
                        stderr.
                      </td>
                    </tr>
                    <tr>
                      <td>
                        <code>130</code>
                      </td>
                      <td>Interrupted with Ctrl-C.</td>
                    </tr>
                    <tr>
                      <td>child code</td>
                      <td>
                        <code>run</code> exits with the child process’s return
                        code.
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </section>

            <section
              id="ci"
              className="sc-docs-section"
              aria-labelledby="ci-title"
            >
              <SectionHeading
                eyebrow="09 / CI"
                title="No browser. No flags. One scope."
                id="ci-title"
              >
                <p>
                  Service tokens are the CI story. Create one, store it as a
                  masked secret, and let the token define the path.
                </p>
              </SectionHeading>

              <h3>Create the token</h3>
              <CodeBlock
                title="token create"
                code={`secria token create \\
  --name github-actions \\
  --access read \\
  --env prod \\
  --expires-in-days 90`}
              />
              <p>
                The token is printed once. Save it directly into your CI
                provider’s secret store; do not commit it or paste it into a
                ticket.
              </p>

              <h3>GitHub Actions</h3>
              <CodeBlock
                title=".github/workflows/deploy.yml"
                code={`name: deploy
on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    env:
      SECRIA_API_URL: https://secria.example.com
      SECRIA_TOKEN: \${{ secrets.SECRIA_TOKEN }}
    steps:
      - uses: actions/checkout@v4
      - run: uvx secria pull --out .env --force
      - run: npm ci
      - run: npm test`}
              />

              <h3>GitLab CI</h3>
              <CodeBlock
                title=".gitlab-ci.yml"
                code={`test:
  image: python:3.12
  variables:
    SECRIA_API_URL: https://secria.example.com
  before_script:
    - pip install uv
    - uvx secria pull --out .env --force
  script:
    - npm ci
    - npm test`}
              />
              <p>
                Add <InlineCode text="SECRIA_TOKEN" /> as a masked CI/CD
                variable. The CLI reads it from the environment; no login step is
                needed.
              </p>

              <h3>Scope rules</h3>
              <ul className="sc-docs-list">
                <li>
                  The token has exactly one workspace/project/environment scope.
                </li>
                <li>
                  Omit <InlineCode text="--workspace" />,{" "}
                  <InlineCode text="--project" />, and{" "}
                  <InlineCode text="--env" />; passing a different one is an
                  error.
                </li>
                <li>
                  <InlineCode text="read" /> is enough for pull, diff, run, list,
                  and get.
                </li>
                <li>
                  <InlineCode text="read_write" /> is required for push, set, and
                  unset.
                </li>
                <li>
                  A service token cannot create another service token, manage
                  members, or change roles.
                </li>
              </ul>

              <Callout tone="tip" title="Rotate tokens on a schedule">
                <p>
                  Give tokens an expiry and rehearse rotation. Because each token
                  is scoped and hashed at rest, replacing one does not disturb
                  other environments. Revoke the old token from the web app when
                  the new one is live.
                </p>
              </Callout>
            </section>

            <section
              id="recipes"
              className="sc-docs-section"
              aria-labelledby="recipes-title"
            >
              <SectionHeading
                eyebrow="10 / Recipes"
                title="Small patterns that save time."
                id="recipes-title"
              >
                <p>
                  Copy these when your repository shape or workflow matches.
                </p>
              </SectionHeading>

              <div className="sc-docs-recipes">
                {RECIPES.map((recipe) => (
                  <article className="sc-docs-recipe" key={recipe.title}>
                    <h3>{recipe.title}</h3>
                    <p>{recipe.body}</p>
                    <CodeBlock
                      code={recipe.code}
                      title={recipe.codeTitle ?? "shell"}
                    />
                  </article>
                ))}
              </div>
            </section>

            <section
              id="troubleshooting"
              className="sc-docs-section"
              aria-labelledby="troubleshooting-title"
            >
              <SectionHeading
                eyebrow="11 / Troubleshooting"
                title="Read the error, then the fix."
                id="troubleshooting-title"
              >
                <p>
                  These are the messages people hit most often. If yours is not
                  here, run <InlineCode text="secria doctor" /> first.
                </p>
              </SectionHeading>

              <div className="sc-docs-trouble">
                {TROUBLESHOOTING.map((item) => (
                  <article className="sc-docs-trouble-item" key={item.symptom}>
                    <h3>
                      <InlineCode text={item.symptom} />
                    </h3>
                    <p>
                      <strong>Why:</strong> <InlineCode text={item.meaning} />
                    </p>
                    <p>
                      <strong>Fix:</strong> <InlineCode text={item.fix} />
                    </p>
                  </article>
                ))}
              </div>
            </section>

            <section
              id="faq"
              className="sc-docs-section"
              aria-labelledby="faq-title"
            >
              <SectionHeading
                eyebrow="12 / FAQ"
                title="Questions that come up fast."
                id="faq-title"
              >
                <p>
                  Short answers, with links back to the relevant section when
                  you need the longer version.
                </p>
              </SectionHeading>

              <div className="sc-docs-faq">
                {FAQ.map((item) => (
                  <details key={item.question}>
                    <summary>{item.question}</summary>
                    <p>
                      <InlineCode text={item.answer} />
                    </p>
                  </details>
                ))}
              </div>

              <div className="sc-docs-cta">
                <div>
                  <p className="sc-docs-eyebrow">Next step</p>
                  <h2>Put your .env on a leash.</h2>
                  <p>
                    Install the CLI, sign in, and link one repository. The first
                    push is usually the moment it clicks.
                  </p>
                </div>
                <div className="sc-docs-cta-actions">
                  <div className="sc-docs-install">
                    <span className="sc-docs-install-label">Install</span>
                    <code translate="no">uv tool install secria</code>
                    <CopyCommand command="uv tool install secria" />
                  </div>
                  <Link className="sc-btn sc-btn--lime" href="/login">
                    Open the vault
                    <ArrowRight size={15} />
                  </Link>
                </div>
              </div>
            </section>
          </article>
        </div>
      </main>

      <MarketingFooter />
    </div>
  );
}
