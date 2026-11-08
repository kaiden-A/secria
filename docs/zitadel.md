# Zitadel setup

Secria uses Zitadel only for identity. Authorization (who can see which
workspace, project, environment, or secret) lives in Secria's own database.

## Applications

One Zitadel Project is enough. Create:

| App | Type | Purpose |
| --- | --- | --- |
| Web | Web / User Agent, Authorization Code + PKCE | Browser login |
| CLI | Native, Device Code grant | `secria login` |

The current development client also supports the device flow, so a separate
Native app is optional for local work. In production, separate apps let you
rotate or disable CLI access without breaking the web app.

## Web app

- Redirect URI: `http://localhost:3000/api/auth/callback`
- Post-logout URI: `http://localhost:3000/login`
- Auth method: PKCE (no client secret)
- Scopes: `openid profile email`
- Require verified email addresses.

Production URIs:

```text
https://app.example.com/api/auth/callback
https://app.example.com/login
```

## CLI app

- Type: Native
- Grant: Device Code (`urn:ietf:params:oauth:grant-type:device_code`)
- Scopes: `openid profile email offline_access`

The CLI prints the verification URL and user code, polls the token endpoint, and
stores the ID token + refresh token in the OS keychain.

## Settings

`.env`:

```env
ZITADEL_ISSUER=https://<instance>.zitadel.cloud
ZITADEL_CLIENT_ID=<client id>
ZITADEL_REDIRECT_URI=http://localhost:3000/api/auth/callback
ZITADEL_POST_LOGOUT_URI=http://localhost:3000/login
# Optional, only if the API should accept access tokens whose audience is the
# Zitadel project rather than the client ID:
ZITADEL_API_AUDIENCE=
```

## How validation works

The API verifies the ID token signature against the instance JWKS, then checks
`iss`, `aud`, `exp`, and the nonce from the login handshake. The first valid
sign-in upserts the local `users` row by `sub`; an invited placeholder row with
the same email is adopted.

CLI bearer tokens are validated the same way. A service token is detected by its
`secria_st_` prefix and looked up by SHA-256 hash instead (Phase 8).

## Web flow in Secria

```text
GET  /api/auth/login?next=/w/acme
  -> signed HttpOnly app_oauth cookie (state, nonce, PKCE verifier, next)
  -> 302 to Zitadel
GET  /api/auth/callback?code=...&state=...
  -> code exchange with the PKCE verifier
  -> ID token verified via JWKS + nonce
  -> users row upserted, sessions row created
  -> HttpOnly secria_session cookie set
  -> 302 to the safe `next` path
POST /api/auth/logout
  -> session row deleted, cookie cleared
  -> { "logoutUrl": "<Zitadel end-session URL>" }
```

`GET /api/v1/me` returns the signed-in user. `GET /api/v1/me/sessions` lists
active web sessions and `DELETE /api/v1/me/sessions/{id}` revokes one.

Sessions are rolling: a session close to expiry is extended while it is used.
Logout deletes the local row and the browser is sent to Zitadel's end-session
endpoint so the IdP cookie does not silently sign the user back in.

## CLI bearer tokens

`secria login` uses the device authorization grant and sends the resulting ID
token as `Authorization: Bearer <jwt>`. The API validates it without a nonce and
upserts the same local user. If `ZITADEL_API_AUDIENCE` is set, an access token
with that audience is accepted too.

The API never accepts a CLI bearer token as a browser session and never falls
back to the cookie when an invalid Authorization header is present.

