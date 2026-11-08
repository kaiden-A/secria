# Security model

## Never in plaintext outside the API

- Secret values are decrypted only inside a FastAPI request that has already
  passed workspace membership, project role, and environment checks.
- Values never enter logs, audit metadata, error messages, traces, or the web
  app's server-side cache.
- The web UI receives a value only from the explicit reveal or download
  endpoint, and both are audited.

## Envelope encryption

```text
SECRIA_MASTER_KEY (KEK, outside DB)
        │  AES-256-GCM wrap
        ▼
project_keys.encrypted_dek (one random 256-bit DEK per project)
        │  AES-256-GCM, fresh 12-byte nonce
        ▼
secret_versions.ciphertext
```

- AAD: `workspace_id:project_id:environment_id:key`. Ciphertext cannot be moved
  between projects, environments, or keys.
- Wrapped project keys use AAD
  `secria:dek:<project_id>:<key_version>:<kek_version>` so a wrapped DEK cannot
  be moved between projects or versions either.
- Every version stores `key_version` (the DEK version) and the KEK version is
  stored on `project_keys`.
- KEK rotation re-wraps project DEKs only. DEK rotation re-encrypts that
  project's values in a background job (not part of the MVP).
- Back up `SECRIA_MASTER_KEY` separately from Neon. Losing it makes every secret
  unrecoverable.

## Tokens

| Token | Format | Storage | Lifetime |
| --- | --- | --- | --- |
| Web session | 32 random bytes, URL-safe | `sessions.token_hash` (SHA-256) | 30 days, rolling |
| Invite | 32 random bytes, URL-safe | `invites.token_hash` (SHA-256) | 7 days |
| Service | `secria_st_<random>` | `service_tokens.token_hash` (SHA-256) | optional expiry |

- All comparisons use constant-time functions.
- Service tokens are scoped to one project + environment and are `read` or
  `read_write`.
- Plaintext tokens are shown once. The API returns a service token only in the
  create response; the invite URL is returned to the admin who created it.

## Authorization

- Workspace roles: `owner`, `admin`, `member`.
- Project roles: `admin`, `editor`, `viewer`.
- Workspace owners/admins see every project. Members see only granted projects.
- `project_member_envs` optionally narrows a grant to specific environments.
- Every handler resolves the resource server-side; inaccessible resources
  return **404**, never 403.
- Removing a member revokes project access immediately. Their audit history is
  retained.

## Rate limits

Auth-adjacent endpoints, invite acceptance, secret reveal, download, diff, and
bulk upsert are rate-limited. Limits are per-IP for anonymous requests and
per-user for authenticated requests. `RATE_LIMIT_ENABLED=false` disables them in
tests.

## Response hygiene

- `Cache-Control: no-store`, `Pragma: no-cache` on every secrets response.
- Bulk upsert is transactional and capped at 1000 keys / 64 KB per value.
- Secret keys must match `^[A-Z_][A-Z0-9_]*$` and are stored in plaintext
  (needed for listing and diffing).
- CORS allows the configured web origin only.
- Cookies: HttpOnly, SameSite=Lax, Secure in production.

## Key rotation runbook (manual)

1. Generate a new 32-byte master key and increment `SECRIA_MASTER_KEY_VERSION`.
2. Keep the old key available during the migration window.
3. Re-wrap every `project_keys.encrypted_dek` with the new KEK and update
   `kek_version`.
4. Verify a reveal in each project.
5. Remove the old key from the environment.

DEK rotation and background re-encryption are a post-MVP job.
