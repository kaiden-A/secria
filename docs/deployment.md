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
RESEND_API_KEY=<key>
EMAIL_FROM="Secria <secria@example.com>"
```

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

## Local Postgres

`docker-compose.yml` provides Postgres on port 5433:

```bash
docker compose up -d postgres
DATABASE_URL=postgresql://secria:secria@localhost:5433/secria?sslmode=disable
```

Do not use the local database with production secrets.
