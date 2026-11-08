# Deployment

## Web (`client/`)

Deploy to Vercel or any Node host.

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
