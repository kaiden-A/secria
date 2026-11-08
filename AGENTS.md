# Secria — repo rules for agents

Self-hosted secrets manager: Workspace → Project → Environment → Secret. The web
app never decrypts; only the FastAPI service touches plaintext or the database.
Read `plan.md` before changing the core, and keep this file current.

## Commands

```bash
npm run start                 # install root, client, server, and cli dependencies
npm run dev                   # both dev servers (api :8000, web :3000)
uv run --directory server pytest
uv run --directory server ruff check .
uv run --directory server ruff format .
uv run --directory server pyright
uv run --directory server alembic upgrade head
uv run --directory cli pytest
npm --prefix client run typecheck
npm --prefix client run lint
npm --prefix client run build
```

Server runs on Python 3.12 via uv. Root `.env` is read by `server/app/config.py`;
never commit it. `.env.example` documents every setting.

## Server invariants

- **Sync** SQLAlchemy 2 + **pg8000** only. Never asyncpg/psycopg. Neon's pooler
  is transaction-mode; do not rely on session state.
- Every table is schema-qualified (`Base.metadata = MetaData(schema=settings.db_schema)`).
- Timestamps are timezone-aware UTC in the DB; API payloads use integer milliseconds.
- snake_case columns; camelCase Pydantic fields (no alias generator).
- Errors are `{"error": "sentence"}`. Services raise `app/services/errors.py`
  exceptions; `main.py` maps them. Routers stay thin.
- Every endpoint resolves IDs server-side and checks workspace membership +
  project role. Return 404 for resources the caller cannot see.
- Only the API decrypts. Never log, cache, or return plaintext outside the
  authorized reveal/download response. Audit logs contain key names and counts,
  never values.
- Alembic migrations are hand-reviewed. The baseline revision matches the
  existing Neon schema (`1b77f308b88f`); never drop or recreate live tables.
  `alembic check`/autogenerate reports schema-qualified FK and enum churn on
  this database; that is a known reflection false positive. Column, index, and
  table diffs are still meaningful.
- Workspace/project/environment APIs use UUID path params. The web app and CLI
  resolve slugs through the list endpoints; slugs are not globally unique below
  the workspace.
- Creating a project requires workspace owner/admin. It creates
  `dev`/`staging`/`prod` and a wrapped project DEK in the same transaction.
- Secret values are versioned. Unchanged bulk values do not create a version;
  updates and restores do. `replace` soft-deletes keys missing from the payload,
  and re-adding a deleted key restores it and continues its version numbers.
- `SecurityHeaders` adds `Cache-Control: no-store` and `Pragma: no-cache` to
  every `/secrets`, `/audit-logs`, and `/service-tokens` response.
- Service tokens are project/environment-scoped. `secret_services` accepts a
  `Principal`: a user goes through `require_project_access`; a token goes through
  `token_services.require_service_access`, which enforces its single scope and
  `read` vs `read_write`. Service tokens cannot call user-only routes.
- Audit rows for token actions use `actor_type="service_token"` and the token id.
- Rate limits live in `app/rate_limit.py` (slowapi, per client IP). The 429 body
  is the standard `{"error": ...}` shape with `Retry-After`.
- `docs/api.md` documents the implemented surface; update it when a router
  changes.
- Tests run against a throwaway schema on the configured Postgres and disable the
  limiter after app import.

## Client invariants

- Next.js 16 App Router; read `client/node_modules/next/dist/docs/` before
  writing Next-specific code if it is unfamiliar.
- `client/proxy.ts` is the route guard (NOT `middleware.ts`); it only checks that
  the session cookie exists. Real authorization is server-side.
- `/api/*` is always the FastAPI rewrite in `next.config.ts`. There are no route
  handlers under `client/app/api/`.
- Session-bearing fetches go through `lib/api-client.ts`; 401 redirects to
  `/login?next=`.
- Server state is TanStack Query. Do not invent a second store.
- `app/globals.css` owns the design tokens and `sc-*` component classes. Reuse
  them instead of adding one-off styles. The dashboard layer covers the app
  shell, project cards, tables, dialogs, menus, diffs, and the invite landing.
- Theme is `data-theme="light|dark"` on `<html>`, defaulting to
  `prefers-color-scheme` and persisted in `localStorage["secria-theme"]`.
  `ThemeToggle` is the only setter; use semantic tokens (`--heading`,
  `--primary`, `--on-dark`, `--on-lime`) instead of hard-coded light colours.
- Dashboard routes: `/w/[ws]` (projects), `/w/[ws]/members`, `/w/[ws]/audit`,
  `/w/[ws]/p/[project]` (secrets), `/access`, `/tokens`, `/settings`, and
  `/invite/[token]`. `ProjectShell` provides the project context to its tabs.
- The visual language is a **secure ledger**: ice-white canvas, petrol-blue
  rail/primary actions, signal lime used sparingly. It is intentionally not a
  clone of neoma-study.

## Auth invariants

- Zitadel OIDC PKCE public client; code exchange server-side. No client secret.
- The PKCE verifier lives only in the signed, HttpOnly, 10-minute `app_oauth`
  cookie.
- Web sessions are rows in `sessions`; the cookie carries a random token and the
  DB stores its SHA-256. Logout deletes the row.
- `dependencies.current_principal` resolves a bearer token first, then the
  session cookie. A present but invalid Authorization header must never fall
  back to the cookie.
- User provisioning requires a verified email. A placeholder row with
  `zitadel_sub IS NULL` is adopted by email on first sign-in.
- CLI uses the device authorization grant and stores tokens in the OS keychain
  (file fallback at mode 0600). It sends a bearer JWT to the API.
- Service tokens are `secria_st_<random>`; only the SHA-256 hash is stored.
  `SECRIA_TOKEN` with that prefix switches the CLI to
  `/api/v1/service-tokens/current` instead of the workspace list endpoints.
- Invite and service tokens are compared with constant-time functions. An invite
  can only be accepted by a logged-in user whose verified email matches.
- `services/permissions.py` owns workspace/project/environment role checks.
  Return 404 for invisible resources and 403 only when the resource is visible
  but the action is not allowed.

## Security invariants

- Envelope encryption: KEK from `SECRIA_MASTER_KEY` → per-project DEK →
  AES-256-GCM with a fresh 12-byte nonce and AAD
  `workspace_id:project_id:environment_id:key`.
- `Cache-Control: no-store` on every secrets response and audit response.
- Audit logs are workspace-owner/admin only. Metadata contains key names,
  counts, roles, and version numbers; never values.
- Bulk upsert is transactional and limited to 1000 keys / 64 KB per value.
- Rate-limit auth-adjacent, invite, reveal, download, and token-creation
  endpoints (slowapi, per IP); tests disable the limiter.
- Strict CORS (web origin only). HTTPS in production. Cookies HttpOnly,
  SameSite=Lax, Secure in production.
- Rotating `SECRIA_MASTER_KEY` requires re-wrapping project DEKs; losing it makes
  every secret unrecoverable.

## Deploy

- Cloud Run `secria` in `asia-southeast1`; image
  `<DOCKERHUB_USERNAME>/secria` from `vars.APP_NAME`. CD is
  `.github/workflows/cd.yml` on pushes to `main` under `server/**`.
- Build context is `./server`; the image is the two-stage uv Dockerfile. Run as
  non-root, listen on `0.0.0.0:${PORT}`.
- Deploys never run migrations. Run `alembic upgrade head` explicitly.
- Set `FORWARDED_ALLOW_IPS=*` on Cloud Run so per-IP throttling sees the real
  client, and `COOKIE_SECURE=true` in production.
- The Vercel client is pinned to `sin1` by `client/vercel.json`; set `API_ORIGIN`
  to the Cloud Run URL.
- CI (`.github/workflows/ci.yml`) runs server, client, and CLI checks on every
  push and pull request.

## Phase status

- Phase 0: scaffold, config, design foundation, CI. **Complete.**
- Phase 1: models, baseline migration, encryption. **Complete.**
- Phase 2: auth/session/permissions. **Complete.**
- Phase 3: workspaces/projects/environments/members. **Complete.**
- Phase 4: secrets/versions/audit. **Complete.**
- Phase 5: invites/email. **Complete.**
- Phase 6: CLI. **Complete.**
- Phase 7: full web UI. **Complete.**
- Phase 8: service tokens/hardening/deployment. **Complete.**
