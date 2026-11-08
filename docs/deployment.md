# Deployment

## Web (`client/`)

Deploy to Vercel or any Node host. `client/vercel.json` pins the Vercel
functions to `sin1` (Singapore, next to Neon and Cloud Run); without it they
default to `iad1` and every API call crosses the Pacific twice.

- Set `API_ORIGIN` to the public FastAPI origin (for example
  `https://api.example.com`). The browser only talks to the web origin because
  `/api/*` is rewritten.
- The web app does not need the database URL, the master key, or the Resend key.
- Add the production callback and post-logout URIs to Zitadel.

## API (`server/`)

Build the Docker image with `server/` as the context:

```bash
docker build -t secria-api ./server
docker run --rm -p 8080:8080 --env-file .env secria-api
```

Production runs on Cloud Run in `asia-southeast1`, the same deploy shape as
neoma-study and solace-garden. The service is `secria`; the image is
`<dockerhub-user>/secria`, built by `.github/workflows/cd.yml`.

- Cloud Run injects `PORT`; the container listens on `0.0.0.0:${PORT}`.
- Set `FORWARDED_ALLOW_IPS=*` on the service so uvicorn trusts Cloud Run's
  `X-Forwarded-For`. Without it the per-IP rate limiter sees the proxy address
  and every caller shares one bucket.
- Point the platform health check at `GET /api/health`.
- Keep the service in `asia-southeast1`, next to Neon.

Required production env:

```env
DATABASE_URL=postgresql://...pooler.../neondb?sslmode=require
DATABASE_URL_DIRECT=postgresql://...direct.../neondb?sslmode=require
SECRIA_MASTER_KEY=<32-byte base64>
SECRIA_MASTER_KEY_VERSION=1
APP_SECRET=<random>
ZITADEL_ISSUER=https://<instance>.zitadel.cloud
ZITADEL_CLIENT_ID=<client id>
ZITADEL_REDIRECT_URI=https://app.example.com/api/auth/callback
ZITADEL_POST_LOGOUT_URI=https://app.example.com/login
APP_URL=https://app.example.com
WEB_ORIGIN=https://app.example.com
COOKIE_SECURE=true
RATE_LIMIT_ENABLED=true
RESEND_API_KEY=<key>
EMAIL_FROM="Secria <secria@example.com>"
```

Also set `CORS_ORIGINS` only if non-browser clients call the API directly; the
web app uses the same-origin `/api/*` rewrite.

## CLI / CI

Point the CLI at the deployed API and Zitadel instance:

```env
SECRIA_API_URL=https://api.example.com
SECRIA_ZITADEL_ISSUER=https://<instance>.zitadel.cloud
SECRIA_ZITADEL_CLIENT_ID=<client id>
```

For CI, create a project/environment token in the dashboard or with
`secria token create`, then expose it as `SECRIA_TOKEN`. Store it as a masked
secret; it is shown only once. Prefer `read` tokens for deploy jobs that only
pull configuration, and set an expiry where the platform supports one.

Migrations are explicit; deploys do not run them automatically:

```bash
uv run --directory server alembic upgrade head
```

## CD

`.github/workflows/cd.yml` mirrors the neoma-study / solace-garden pipeline:

1. Trigger on pushes to `main` that touch `server/**`.
2. Build `server/Dockerfile` with context `./server`.
3. Push `<DOCKERHUB_USERNAME>/<APP_NAME>:<short-sha>` and `:latest`.
4. Deploy that tag to Cloud Run in `asia-southeast1`.

Repository configuration:

| Kind | Name | Value |
|---|---|---|
| secret | `DOCKERHUB_USERNAME` | Docker Hub account |
| secret | `DOCKERHUB_TOKEN` | Docker Hub access token |
| secret | `GCP_SA_KEY` | service-account JSON |
| variable | `APP_NAME` | `secria` |

The deploy service account needs `roles/run.developer` and
`roles/iam.serviceAccountUser` on the Cloud Run runtime service account.

The workflow is pinned to `main`; a `master`/`main` mismatch means it never
fires. It only rebuilds the API — the Vercel client deploys from the same push
through its git integration. Migrations stay manual (above).

## Database

- Use the pooled Neon URL for the API and the direct URL for Alembic.
- Enable Neon point-in-time restore.
- Back up the master key outside Neon. A database restore without the KEK is
  useless for secret values.

## Health

`GET /api/health` executes `select 1`. Point the platform health check at it.

## Proxy and limits

Rate limits key off the client address. If the API runs behind a reverse proxy
or load balancer, start uvicorn with `--proxy-headers` and set
`FORWARDED_ALLOW_IPS` to the proxy address(es); otherwise every request appears
to come from the proxy and shares one bucket. Never trust forwarded headers when
the API is directly reachable.

## Local Postgres

`docker-compose.yml` provides Postgres on port 5433:

```bash
docker compose up -d postgres
DATABASE_URL=postgresql://secria:secria@localhost:5433/secria?sslmode=disable
```

Do not use the local database with production secrets.
