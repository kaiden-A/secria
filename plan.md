Secria: Architecture and Build Prompt
A self-hosted secrets manager (Doppler-style) built on Next.js, FastAPI, Neon Postgres and Zitadel. Part 1 is the architecture. Part 2 is a prompt you can paste into an AI coding agent (Claude Code, Cursor, etc.) to build it phase by phase.
Assumptions to confirm
• Your "environment" is treated as the top-level container, called a Workspace here. Doppler uses "environment" for dev/staging/prod, so Secria adds that layer inside each project: Workspace → Project → Environment (dev, staging, prod) → Secrets. Without it, secria push .env would have no target to write to.
• Secrets are encrypted by the app (envelope encryption), not just by Neon's disk encryption.
• The CLI is Python (Typer) for the MVP. It can be rewritten in Go later for single-binary distribution.
• Authorization (who can see which project) lives in Secria's own database. Zitadel only proves who someone is.
Part 1: Architecture
1. System overview
• Web (Next.js, App Router): dashboard for workspaces, projects, environments, secrets, members, invites and audit log.
• API (FastAPI): the only component that touches the database and the encryption keys. Both the web app and the CLI call it.
• DB (Neon Postgres): metadata plus encrypted secret values.
• Auth (Zitadel): OIDC login for humans (web and CLI). The API validates its JWTs.
• CLI (secria): login via device flow, push and pull .env files, run commands with injected secrets.
• Email (Resend or SMTP): sends invitations.
Flow: Browser or CLI → Zitadel (login) → access token → FastAPI (validates JWT via JWKS, checks membership, encrypts or decrypts) → Neon.
The Next.js server never decrypts anything itself. It forwards the user's access token to FastAPI. Keep one place that handles plaintext secrets.
2. Tech choices
• Next.js 15, TypeScript, Tailwind, shadcn/ui, TanStack Query. Auth via next-auth (Auth.js) with the Zitadel OIDC provider, or oidc-client-ts. Use Authorization Code + PKCE.
• FastAPI, Python 3.12, SQLAlchemy 2.0 (async) with asyncpg, Alembic, Pydantic v2, python-jose or authlib for JWT validation, cryptography for AES-GCM, slowapi for rate limiting.
• Neon: use the pooled connection string for the API, the direct string for Alembic migrations. Use a Neon branch per dev and per PR.
• Zitadel (cloud or self-hosted): one Project, three applications: Web (PKCE, public), API (API app, JWT validation), CLI (Native app with Device Code grant).
• CLI: Typer, httpx, keyring for token storage, python-dotenv parser, rich for output.
• Monorepo with pnpm workspaces and uv:
secria/
  apps/web/        # Next.js
  apps/api/        # FastAPI
  apps/cli/        # Typer CLI
  packages/        # shared types / generated OpenAPI client
  docker-compose.yml
3. Domain model
• User: mirrors a Zitadel identity, keyed by the sub claim.
• Workspace: top-level container. Has owner(s) and members.
• Project: belongs to one workspace. Contains environments.
• Environment: belongs to one project (default: dev, staging, prod). Holds secrets.
• Secret: key plus encrypted value, per environment, versioned.
• Invite: email-based invitation to a workspace with a list of project grants.
Roles
• Workspace roles: owner, admin, member. Owners and admins manage members and see all projects. Members see only projects they are granted.
• Project roles (per member, per project): admin, editor (read and write), viewer (read only).
• Optional later: restrict a grant to specific environments (e.g. contractor sees dev only).
Effective permission check on every request: workspace membership → project grant (or workspace admin) → role allows the action → if the action touches an environment, the grant allows it.
4. Database schema (PostgreSQL)
Use UUID primary keys (uuid_generate_v7 or gen_random_uuid()), created_at and updated_at everywhere, and soft-delete only where noted.
users(id, zitadel_sub UNIQUE, email, name, last_login_at)

workspaces(id, name, slug UNIQUE, created_by)
workspace_members(workspace_id, user_id, role)            -- PK (workspace_id, user_id)

projects(id, workspace_id, name, slug, description, archived_at)
  UNIQUE(workspace_id, slug)
project_members(project_id, user_id, role)                -- PK (project_id, user_id)
project_member_envs(project_id, user_id, environment_id)  -- optional env-level restriction

environments(id, project_id, name, slug, position)
  UNIQUE(project_id, slug)
project_keys(project_id, key_version, encrypted_dek, created_at)  -- envelope encryption

secrets(id, environment_id, key, current_version_id, deleted_at)
  UNIQUE(environment_id, key)
secret_versions(id, secret_id, version, ciphertext, nonce, key_version,
                created_by, created_at, comment)

invites(id, workspace_id, email, role, token_hash, invited_by,
        expires_at, accepted_at, revoked_at)
invite_grants(invite_id, project_id, role)

service_tokens(id, project_id, environment_id, name, token_hash,
               access ENUM('read','read_write'), expires_at, last_used_at, revoked_at)

audit_logs(id, workspace_id, project_id, environment_id, actor_type,
           actor_id, action, target, metadata JSONB, ip, user_agent, created_at)
Indexes: workspace_members(user_id), project_members(user_id), secrets(environment_id), audit_logs(workspace_id, created_at DESC), invites(email).
Secret keys are stored in plaintext (needed for listing and diffing). Only values are encrypted. Keys must match ^[A-Z_][A-Z0-9_]*$.
5. Encryption design
Envelope encryption:
1. A master key (KEK) lives outside the database: env var SECRIA_MASTER_KEY (32 bytes, base64) for the MVP. Later move to AWS KMS, GCP KMS or HashiCorp Vault.
2. Each project has a random 256-bit DEK, stored in project_keys encrypted with the KEK.
3. Each secret value is encrypted with the project's DEK using AES-256-GCM with a fresh 12-byte random nonce. Use workspace_id:project_id:environment_id:key as AAD so ciphertext can't be moved between secrets.
4. Rotation: key_version on every ciphertext. Rotating the KEK re-encrypts only the DEKs. Rotating a DEK re-encrypts that project's values in a background job.
5. Decrypt only inside the API request that needs it. Never log, cache or return plaintext outside the response body of authorized endpoints.
6. Authentication and authorization
Web
• Authorization Code + PKCE against Zitadel. The Next.js session holds the access token (server-side only, httpOnly cookie).
• Next.js route handlers or server actions call FastAPI with Authorization: Bearer <access_token>.
API
• Validate JWT signature via Zitadel JWKS (cached), plus iss, aud and exp.
• On first valid request, upsert the users row from sub, email and name. Require email_verified.
• A FastAPI dependency current_user plus permission helpers: require_workspace_role(...), require_project_role(...).
CLI
• Device Authorization Grant (RFC 8628), which Zitadel supports. secria login prints a URL and code, opens the browser, polls for the token.
• Store access and refresh tokens in the OS keychain through keyring. Fall back to ~/.config/secria/credentials.json with 0600 permissions.
• Refresh automatically when the access token is close to expiry.
CI and servers (service tokens)
• Scoped to one project and environment, read-only by default. Format: secria_st_<random>.
• Show the plaintext once, store only a SHA-256 hash.
• Used through SECRIA_TOKEN env var, so no browser login is needed.
7. Invitation flow
1. An admin enters an email, picks a workspace role and ticks the projects (with a role each).
2. API creates invites plus invite_grants, generates a random token, stores its hash, sets expiry (7 days) and emails a link https://app/invite/<token>.
3. The invitee opens the link and logs in via Zitadel (creating an account if needed).
4. The API checks token validity and that the logged-in verified email matches the invited email, then creates workspace_members and project_members rows, and marks the invite accepted.
5. Admins can resend, revoke, and edit project access any time. Removing a member revokes their access immediately, and all their actions stay in the audit log.
8. API surface (all under /api/v1)
GET    /me

POST   /workspaces                       GET /workspaces
GET    /workspaces/{ws}                  PATCH /workspaces/{ws}
GET    /workspaces/{ws}/members          PATCH|DELETE /workspaces/{ws}/members/{user}
POST   /workspaces/{ws}/invites          GET /workspaces/{ws}/invites
POST   /invites/{token}/accept           DELETE /workspaces/{ws}/invites/{id}
POST   /workspaces/{ws}/invites/{id}/resend

POST   /workspaces/{ws}/projects         GET /workspaces/{ws}/projects
GET|PATCH|DELETE /projects/{project}
PUT    /projects/{project}/members/{user}     DELETE same
POST   /projects/{project}/environments

GET    /projects/{p}/environments/{e}/secrets          -- masked list (keys, updated_at)
GET    /projects/{p}/environments/{e}/secrets/download -- plaintext, format=json|env
PUT    /projects/{p}/environments/{e}/secrets          -- bulk upsert {secrets, mode: merge|replace}
POST   /projects/{p}/environments/{e}/secrets/diff     -- compare local vs remote (keys + hash only)
GET|DELETE /projects/{p}/environments/{e}/secrets/{key}
GET    /projects/{p}/environments/{e}/secrets/{key}/versions
POST   /projects/{p}/environments/{e}/secrets/{key}/rollback

POST|GET|DELETE /projects/{p}/environments/{e}/service-tokens
GET    /workspaces/{ws}/audit-logs?project=&actor=&action=&cursor=
The CLI-friendly endpoints are bulk upsert, download and diff. Bulk upsert must be transactional.
9. CLI design
Binary name: secria.
secria login | logout | whoami
secria workspace list | use <slug>
secria project list | create <name> [--from-env .env] [--env dev]
secria init                      # link current dir -> workspace/project/env, writes .secria.yaml
secria push [FILE=.env] [--env dev] [--project x] [--replace] [--dry-run] [--yes]
secria pull [--env dev] [--project x] [--out .env] [--format env|json|yaml] [--force]
secria diff [FILE=.env] [--env dev]
secria run [--env dev] -- <command>     # inject secrets as env vars, nothing written to disk
secria secrets list | get KEY | set KEY=VALUE | unset KEY
secria env list | create <name>
secria token create --env prod --name ci-github     # service token
Key behaviours
• .secria.yaml (safe to commit, contains no secrets): workspace, project, environment. Flags override it.
• secria project create myapp --from-env .env: create the project (default envs dev, staging, prod), parse .env, upload to dev (or --env), write .secria.yaml. Prompt to add .env to .gitignore if it isn't there.
• secria push shows a summary first: +3 added, ~2 changed, 0 removed (keys only, never values), then asks for confirmation unless --yes. Default mode is merge. --replace deletes remote keys missing locally and needs an extra confirmation.
• secria pull refuses to overwrite an existing .env without --force (or shows a diff), writes with file mode 0600, preserves nothing but KEY=VALUE lines unless --keep-comments is added later.
• .env parsing: support export KEY=VAL, quotes, multiline values in double quotes, # comments, and ${VAR} references stored as-is (no expansion).
• Output hygiene: never print values unless the command is explicitly get or --reveal. Exit codes: 0 ok, 1 error, 2 auth, 3 permission, 4 conflict.
• Auth resolution order: SECRIA_TOKEN env var → keychain session → prompt to run secria login.
• Config: SECRIA_API_URL override for self-hosting and local dev.
10. Web UI pages
• /login, /invite/[token]
• /w/[ws]: projects list, create project
• /w/[ws]/members: members and pending invites, invite dialog with per-project role checklist
• /w/[ws]/audit: filterable audit log
• /w/[ws]/p/[project]: environment tabs; secrets table with masked values, click-to-reveal (audited), inline edit, bulk import/export .env into a chosen environment, server-side copy between environments with diff preview, version history, rollback
• /w/[ws]/p/[project]/access: who can access this project and their role
• /w/[ws]/p/[project]/tokens: service tokens
• /settings: CLI sessions, personal info
11. Security checklist
• Plaintext only inside the API process. No secret values in logs, error messages, Sentry events, or the audit log (log key names and counts only).
• Reveal and download actions are always written to the audit log.
• Constant-time comparison for tokens. Hash invite and service tokens.
• Rate limit auth-adjacent and download endpoints. Cap bulk upsert size (e.g. 1000 keys, 64 KB per value).
• Strict CORS (web origin only). Cache-Control: no-store on every secrets response. HTTPS only.
• Never trust IDs from the client: always resolve project to workspace and verify membership server-side (prevents IDOR).
• Return 404 instead of 403 for resources the user can't see.
• Backups: Neon point-in-time restore. Back up the KEK separately. If it's lost, every secret is unrecoverable.
• Treat a leaked .env pushed to git as the user's job, but warn in the CLI when .env isn't gitignored.
12. Deployment
• Web on Vercel (or any Node host). API on Fly.io, Railway or a VPS in Docker. Put the API behind HTTPS and set the Zitadel redirect URIs accordingly.
• Env vars for the API: DATABASE_URL, DATABASE_URL_DIRECT, SECRIA_MASTER_KEY, ZITADEL_ISSUER, ZITADEL_AUDIENCE, WEB_ORIGIN, RESEND_API_KEY, APP_URL.
• Local dev: docker-compose with a local Postgres or a Neon dev branch, plus a Zitadel dev instance.
Part 2: Instruction prompt for your coding agent
Copy everything below this line into your AI coding tool. Build one phase at a time and review each before moving on.
You are a senior full-stack engineer building "Secria", a self-hosted secrets
manager similar to Doppler. Follow the architecture below strictly. Ask me before
deviating from it. Build in the phases listed and stop after each phase so I can
review.

## Product
Hierarchy: Workspace -> Project -> Environment (dev/staging/prod) -> Secrets.
Users are invited to a workspace by email and granted access per project with
a role (admin / editor / viewer). A CLI named `secria` lets developers push a
local .env into a project, pull secrets into .env, diff, and run commands with
injected secrets.

## Stack (do not substitute)
- Monorepo: pnpm workspaces + uv. Folders: apps/web, apps/api, apps/cli.
- apps/web: Next.js 15 App Router, TypeScript, Tailwind, shadcn/ui,
  TanStack Query, Auth.js with Zitadel OIDC (Authorization Code + PKCE).
- apps/api: FastAPI, Python 3.12, SQLAlchemy 2 async + asyncpg, Alembic,
  Pydantic v2, cryptography (AES-256-GCM), slowapi, structlog.
- DB: Neon Postgres (pooled URL for the app, direct URL for migrations).
- Auth: Zitadel. The API validates JWTs via JWKS (iss, aud, exp, signature).
  The CLI uses OAuth2 Device Authorization Grant.
- apps/cli: Python, Typer, httpx, keyring, python-dotenv parsing, rich.
- Email: Resend.

## Non-negotiable rules
1. Only the FastAPI service reads/writes the database and handles plaintext
   secrets. The Next.js app never decrypts; it forwards the user's access token.
2. Authorization lives in our DB (workspace_members, project_members). Zitadel
   is for identity only. Every endpoint must verify workspace membership and
   project role server-side. Return 404 for resources the user cannot access.
3. Encrypt secret values with envelope encryption: master key from
   SECRIA_MASTER_KEY -> per-project DEK (stored encrypted) -> AES-256-GCM per
   value with random 12-byte nonce and AAD = workspace_id:project_id:
   environment_id:key. Store key_version for rotation. Secret key names are
   plaintext; values are ciphertext.
4. Never log, print, or put secret values in errors, audit logs, or traces.
   Audit logs record action, actor, target key names, counts, IP, user agent.
5. Secrets are versioned. Updates create a new secret_versions row; support
   history and rollback.
6. Bulk upsert is transactional and size-limited (1000 keys, 64 KB/value).
7. Invite and service tokens are random, shown once, stored as SHA-256 hashes.
   An invite can only be accepted by a logged-in user whose verified email
   matches the invited email.
8. Add `Cache-Control: no-store` on all secrets responses.
9. Write tests (pytest + httpx AsyncClient) for permission checks, encryption
   round-trip, invite acceptance, and bulk upsert. Include negative tests for
   cross-workspace access (IDOR).
10. Use type hints everywhere, ruff + mypy on the API, eslint + tsc on web.
    Generate an OpenAPI client for web from the FastAPI schema.

## Data model
(Use the schema from the architecture doc: users, workspaces, workspace_members,
projects, project_members, project_member_envs (optional), environments,
project_keys, secrets, secret_versions, invites, invite_grants, service_tokens,
audit_logs.)

## API
(Implement the endpoint list from the architecture doc under /api/v1.)

## CLI commands
login, logout, whoami, workspace list/use, project list/create [--from-env],
init, push, pull, diff, run, secrets list/get/set/unset, env list/create,
token create. Link a directory with .secria.yaml (workspace, project,
environment; never secrets). Auth order: SECRIA_TOKEN -> keychain session.
push must show a key-only summary (+added ~changed -removed) and ask to
confirm unless --yes; --replace requires extra confirmation. pull must not
overwrite an existing file without --force, and writes with mode 0600.
Warn if .env is not in .gitignore.

## Phases (stop after each one)
Phase 0: Monorepo scaffold, docker-compose, env templates, CI (lint + tests),
         README with setup steps for Zitadel apps (Web, API, CLI device flow).
Phase 1: DB models + Alembic migrations + encryption module with tests.
Phase 2: Auth: JWT validation, user upsert, /me, permission dependencies.
Phase 3: Workspaces, projects, environments, members, project grants.
Phase 4: Secrets CRUD, bulk upsert, download, diff, versions, rollback, audit log.
Phase 5: Invites (create, email, accept, revoke, resend).
Phase 6: CLI MVP: login (device flow), init, project create --from-env,
         push, pull, diff, run.
Phase 7: Web UI: login, workspaces, projects, secrets table, members/invites,
         access page, audit log.
Phase 8: Service tokens, rate limiting, hardening pass against the security
         checklist, deployment docs.

## Output format for each phase
1. Short plan and any questions or assumptions.
2. The code, file by file with paths.
3. How to run and test it.
4. A list of what is NOT done yet.

Start with Phase 0 only.
Suggested next steps
• Set up Zitadel first: create a Project with three apps (Web: Code + PKCE, API: JWT, CLI: Native with Device Code). The agent needs the issuer URL, audience and client IDs.
• Generate a master key: python -c "import os,base64;print(base64.b64encode(os.urandom(32)).decode())". Keep a copy somewhere other than your database.
• Features worth adding after the MVP: secret references between projects, webhooks on change, per-environment grants, secret rotation reminders, SSO group sync from Zitadel, and a secria sync for GitHub Actions or Vercel.