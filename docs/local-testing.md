# Try Secria locally

## What works right now

All planned phases are implemented:

- Dashboard: projects, environments, secret reveal/copy/download, import `.env`,
  version history and rollback, members, invites, project access, service tokens,
  audit log, sessions, and settings.
- API: Zitadel PKCE login, web sessions, workspace/project/environment/member
  management, versioned secrets, audits, invites/email, and scoped service tokens.
- CLI: device-flow login, `init`, `push`, `pull`, `diff`, `run`, `secrets`,
  `workspace`/`project`/`env` commands, and `token create`.
- Tests: `npm run test` runs both the API suite and the CLI suite against a
  throwaway schema on the configured database.

## Start

```bash
npm run start       # install root, client, server, and CLI dependencies
npm run dev         # API on :8000, web on :3000
```

Check:

- Web: <http://localhost:3000>
- Login: <http://localhost:3000/login>
- API health: <http://localhost:8000/api/health>
- OpenAPI: <http://localhost:8000/docs>

The API can also be reached through the web origin at
`http://localhost:3000/api/...`; that is the path that carries the HttpOnly
session cookie.

## Log in

The login page submits to `/api/auth/login`, which redirects to Zitadel. After
the callback, the browser has the `secria_session` cookie and lands on the
dashboard.

Requirements:

- The Zitadel web app allows `http://localhost:3000/api/auth/callback`.
- The post-logout URI is `http://localhost:3000/login`.
- The signed-in Zitadel user has a verified email. Unverified emails return 403.

After login, open <http://localhost:3000/api/v1/me>. The session cookie is sent
through the Next rewrite and you should see your user JSON. You can also start
the flow with `http://localhost:3000/login?next=/api/v1/me`.

## Walk through the dashboard

1. Create a workspace, then a project. The project is provisioned with `dev`,
   `staging`, and `prod` plus its own wrapped encryption key.
2. Add a secret in `dev`, reveal it, then edit it and open **Version history** to
   see version 2. Roll back to version 1; Secria writes version 3 instead of
   re-pointing history.
3. Open **Tokens** on the project and create a read-only token for `dev`. Copy it
   immediately; it is shown once.
4. Open **Members** and invite a teammate. With no `RESEND_API_KEY`, the invite
   dialog shows a copyable link instead of sending email.
5. Open **Audit** to see the reveal, update, rollback, token, and invite events.
   Values never appear there.
6. Use the moon/sun button in the topbar to switch themes. The choice persists;
   with no saved choice, Secria follows the operating system.

## Try the CLI

```bash
uv run --directory cli secria login
uv run --directory cli secria init                 # link this directory
uv run --directory cli secria push .env --env dev
uv run --directory cli secria diff .env
uv run --directory cli secria pull --env prod --out .env.prod --force
uv run --directory cli secria run --env dev -- npm start
uv run --directory cli secria secrets list
uv run --directory cli secria secrets get DATABASE_URL
uv run --directory cli secria token create --env dev --name ci-local
```

The CLI reads `SECRIA_API_URL` (default `http://localhost:8000`) and the Zitadel
issuer/client from the environment or the repository `.env`.

### Use a service token like CI would

Create a `read` or `read_write` token in the dashboard or with
`secria token create`, then:

```powershell
$env:SECRIA_TOKEN = "secria_st_..."
$env:SECRIA_API_URL = "http://localhost:8000"
uv run --directory cli secria whoami
uv run --directory cli secria secrets list
uv run --directory cli secria pull --out .env.ci --force
```

```bash
export SECRIA_TOKEN="secria_st_..."
export SECRIA_API_URL="http://localhost:8000"
uv run --directory cli secria whoami
uv run --directory cli secria secrets list
uv run --directory cli secria pull --out .env.ci --force
```

`whoami` prints the token's workspace/project/environment scope. The CLI ignores
the link file's other environments in this mode and rejects an explicit
`--env`/`--project` that does not match the token. A read token can list,
reveal, and download; writes return 403. Service tokens cannot create other
tokens or use `/me`, workspace, project, or member endpoints.

## Exercise the API from the browser console

The session cookie is same-origin, so these calls work after login.

```js
const json = (r) => r.json();
const post = (url, body) =>
  fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }).then(json);

const workspace = await post("/api/v1/workspaces", { name: "Acme" });
const project = await post(`/api/v1/workspaces/${workspace.id}/projects`, {
  name: "My API",
});
const env = project.environments[0];

await fetch(`/api/v1/projects/${project.id}/environments/${env.id}/secrets`, {
  method: "PUT",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    mode: "merge",
    secrets: [{ key: "DATABASE_URL", value: "postgres://local" }],
  }),
}).then(json);

await fetch(
  `/api/v1/projects/${project.id}/environments/${env.id}/secrets`,
).then(json);

await fetch(
  `/api/v1/projects/${project.id}/environments/${env.id}/secrets/DATABASE_URL`,
).then(json); // reveal; audited

await fetch(
  `/api/v1/workspaces/${workspace.id}/audit-logs`,
).then(json);
```

## Run the tests

```bash
npm run test
npm run lint
npm run typecheck
npm run build
```

Or individually:

```bash
uv run --directory server pytest
uv run --directory cli pytest
uv run --directory server ruff check .
uv run --directory server pyright
npm --prefix client run lint
npm --prefix client run typecheck
npm --prefix client run build
```

The API tests create a unique schema on the configured Postgres, fake Zitadel,
disable rate limiting, and clean up after themselves. They do not touch the live
`public` tables. To exercise the limiter manually, leave
`RATE_LIMIT_ENABLED=true` and repeat a login or reveal request; the API returns
`429` with a `Retry-After` header once a limit is hit.

## Database

```bash
uv run --directory server alembic current
uv run --directory server alembic upgrade head
uv run --directory server python scripts/check_db.py
```

`alembic upgrade head` is a no-op on the provisioned Neon database. Do not run
`alembic downgrade` against Neon.

## Troubleshooting

- **Callback fails**: check the Zitadel app's redirect URI and that the client is
  a PKCE public client with the code grant.
- **403 after login**: the IdP email is not verified.
- **Cookie missing**: use `localhost:3000`, not a different hostname; the cookie
  is scoped to the web origin.
- **API on :8000 has no session**: the cookie belongs to :3000. Use the
  `http://localhost:3000/api/...` rewrite or a bearer/service token.
- **429 Too many requests**: wait for `Retry-After` or set
  `RATE_LIMIT_ENABLED=false` while load-testing locally.
- **Invite email not sent**: `RESEND_API_KEY` is empty; use the copyable link.
- **Neon `ConnectionResetError` in tests**: known flaky pg8000/Neon failure;
  rerun.
- **Secrets 503**: `SECRIA_MASTER_KEY` is missing or invalid, or the project has
  no `project_keys` row.
