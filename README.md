# Secria

Secria is a self-hosted secrets manager: a Doppler-style vault built on Next.js,
FastAPI, Neon Postgres, and Zitadel. It stores secrets with envelope encryption,
versions every change, and records who revealed or downloaded what.

```text
Workspace → Project → Environment (dev / staging / prod) → Secret
```

## Why the extra layer?

Doppler calls dev/staging/prod “environments”. Secria treats the top-level
container as a **workspace**, each workspace holds **projects**, and each project
holds its own **environments**. That gives `secria push .env` a precise target and
keeps unrelated projects isolated.

## Architecture

```text
Browser ──→ Next.js (no decryption) ──→ FastAPI ──→ Neon Postgres
   │              │                       │
   └── Zitadel ───┘                       └── AES-256-GCM / project DEKs
CLI ──→ Zitadel device flow ──→ FastAPI
CI  ──→ service token ────────→ FastAPI
```

- **Web** (`client/`): Next.js 16 App Router, TanStack Query, bespoke
  petrol/ice/lime design system. The browser talks to `/api/*`, which Next
  rewrites to FastAPI; the API session cookie is same-origin.
- **API** (`server/`): FastAPI, sync SQLAlchemy 2 + pg8000, Alembic, Pydantic v2,
  AES-256-GCM envelope encryption. It is the only service that reads plaintext.
- **CLI** (`cli/`): Typer, httpx, keyring, rich. Push/pull `.env`, diff, run
  commands with injected secrets, create service tokens.
- **Database**: Neon Postgres, pooled URL for the API, optional direct URL for
  migrations. The existing schema is already provisioned at Alembic revision
  `1b77f308b88f`; the baseline migration matches it without destructive changes.
- **Auth**: Zitadel. Web uses Authorization Code + PKCE with a server-side
  session. CLI uses the Device Authorization Grant. Service tokens are scoped to
  one project/environment with read or read-write access.

## Repository layout

```text
secria/
├── client/      Next.js 16 web app
├── server/      FastAPI API, Alembic, tests
├── cli/         Typer CLI
├── docs/        Zitadel, security, deployment notes
├── plan.md      original architecture + phase prompt
├── .env         local secrets (never committed)
└── package.json root orchestration only
```

## Requirements

- Node.js 22+
- Python 3.12 via [uv](https://docs.astral.sh/uv/)
- A Neon Postgres database
- A Zitadel instance with a PKCE public client (the same client supports the
  device flow for the CLI)

## Setup

1. **Install dependencies**

   ```bash
   npm run start
   ```

2. **Configure environment**

   ```bash
   cp .env.example .env
   ```

   Fill in `DATABASE_URL`, `ZITADEL_ISSUER`, `ZITADEL_CLIENT_ID`, and the
   redirect URIs. Generate the two application secrets:

   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(48))"                    # APP_SECRET
   python -c "import os,base64; print(base64.b64encode(os.urandom(32)).decode())"  # SECRIA_MASTER_KEY
   ```

   Back up `SECRIA_MASTER_KEY` somewhere other than the database. If it is lost,
   every secret is unrecoverable.

3. **Zitadel**

   - Create one Project.
   - Create a **Web** application with Authorization Code + PKCE, no client
     secret. Redirect URI: `http://localhost:3000/api/auth/callback`.
   - Post-logout URI: `http://localhost:3000/login`.
   - Enable the **Device Code** grant on the same application (or create a
     Native app and set its client ID in `ZITADEL_CLIENT_ID` for the CLI).
   - Copy the client ID into `.env`.

   See `docs/zitadel.md` for production URIs and screenshots-free steps.

4. **Database**

   The repository baseline migration matches the provisioned Neon schema at
   revision `1b77f308b88f`. Verify the connection and revision:

   ```bash
   uv run --directory server python scripts/check_db.py
   uv run --directory server alembic current
   ```

   `alembic upgrade head` is a no-op on the existing database and creates the
   full schema on a fresh one:

5. **Run**

   ```bash
   npm run dev
   ```

   Web: <http://localhost:3000> · API: <http://localhost:8000> · API docs:
   <http://localhost:8000/docs> · Implemented surface: `docs/api.md` ·
   Local walkthrough: `docs/local-testing.md`

## Commands

```bash
npm run dev                 # API + web
npm run test                # server + CLI tests
npm run lint                # ruff + eslint
npm run typecheck           # pyright + tsc
npm run build               # production Next build

uv run --directory server alembic upgrade head
uv run --directory server alembic revision --autogenerate -m "change"
```

## Dashboard

After signing in at <http://localhost:3000>:

- Create a workspace and a project; the project gets `dev`, `staging`, `prod`,
  its own encryption key, and default access for workspace admins.
- Manage secrets per environment: reveal/copy (audited, auto-hides after 30s),
  create, edit, import `.env` with a hash-only diff preview, download, delete,
  version history, and rollback.
- Invite people with a workspace role and optional per-project grants; manage
  direct project access and environment restrictions.
- Create scoped service tokens and revoke them immediately.
- Review the audit log with project, action, and actor filters.
- Switch between light and dark with the moon/sun button in the topbar. The
  choice is saved; otherwise Secria follows your OS preference.

## CLI

```bash
uv run --directory cli secria --help
uv run --directory cli secria login
uv run --directory cli secria init                 # link this directory
uv run --directory cli secria push .env --env dev
uv run --directory cli secria diff .env
uv run --directory cli secria pull --env prod --out .env.prod --force
uv run --directory cli secria run --env dev -- npm start
uv run --directory cli secria secrets list
uv run --directory cli secria secrets get DATABASE_URL
uv run --directory cli secria token create --env prod --name ci-github
```

- `push` shows a key-only diff and asks before writing. `--replace` asks again.
- `pull` refuses to overwrite without `--force` and writes mode `0600`.
- `run` injects secrets in memory; it does not create a file.
- Auth order is `SECRIA_TOKEN` → stored device-flow session. Tokens live in the
  OS keychain, with a `0600` file fallback.
- The CLI reads only `SECRIA_API_URL`, `SECRIA_ZITADEL_*`, `ZITADEL_ISSUER`, and
  `ZITADEL_CLIENT_ID` from a local `.env`; server secrets are never loaded into
  `secria run` subprocesses.

## Environment variables

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | Neon pooled connection string |
| `DATABASE_URL_DIRECT` | Optional direct URL for migrations |
| `DB_SCHEMA` | Explicit Postgres schema (default `public`) |
| `SECRIA_MASTER_KEY` | 32-byte base64 KEK |
| `SECRIA_MASTER_KEY_VERSION` | KEK version for rotation |
| `APP_SECRET` | Signs the OAuth handshake cookie |
| `ZITADEL_ISSUER` | Zitadel instance URL |
| `ZITADEL_CLIENT_ID` | PKCE public client / device-flow client |
| `ZITADEL_REDIRECT_URI` | Web callback URL |
| `ZITADEL_POST_LOGOUT_URI` | Post-logout landing page |
| `ZITADEL_API_AUDIENCE` | Optional access-token audience for CLI bearer auth |
| `APP_URL` | Public web URL used in invite links |
| `WEB_ORIGIN` | Allowed CORS origin |
| `SECRIA_SESSION_COOKIE_NAME` | Web session cookie (default `secria_session`) |
| `SESSION_TTL_DAYS` | Rolling session lifetime (default 30) |
| `COOKIE_SECURE` | Secure cookie flag; `true` in production |
| `RATE_LIMIT_ENABLED` | Enable request rate limits |
| `ENVIRONMENT` | `development` or `production` (JSON logs) |
| `LOG_LEVEL` | structlog level |
| `RESEND_API_KEY` | Email delivery; empty = log only |
| `EMAIL_FROM`, `EMAIL_REPLY_TO`, `EMAIL_OVERRIDE_TO` | Sender + dev override |

## Security model

- Only FastAPI decrypts or writes secret values.
- Per-project DEKs are wrapped by the master key; secret values use AES-256-GCM
  with a random 12-byte nonce and an AAD binding workspace, project,
  environment, and key.
- Every update creates a new `secret_versions` row; rollback creates a new
  version from the old plaintext.
- Reveal and download are always audited. Audit metadata contains key names and
  counts, never values.
- Bulk upsert is transactional and limited to 1000 keys and 64 KB per value.
- Secrets responses are `Cache-Control: no-store`.
- Invite and service tokens are random, shown once, and stored as SHA-256 hashes.
- Inaccessible resources return 404, not 403.

See `docs/security.md` for the full checklist and key-rotation runbook.

## Status

Phases 0–8 are complete: the monorepo scaffold, configuration, design
foundation, CI, database models, baseline migration, envelope encryption,
Zitadel PKCE login, web sessions, bearer-JWT validation, `/me`, workspace /
project / environment / member APIs, versioned secrets with bulk upsert and
rollback, audit logs, invites and Resend email, the Typer CLI, the full Next.js
dashboard, scoped service tokens, and rate-limit hardening. See `AGENTS.md` for
the phase log and `docs/local-testing.md` for a guided local walkthrough.

## License

Private. All rights reserved.
