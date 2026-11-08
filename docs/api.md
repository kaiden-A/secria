# API reference (implemented surface)

Base path: `/api`. JSON errors are `{"error": "sentence"}`; validation errors add
`safe details` without echoing submitted values. Timestamps are integer
milliseconds.

## Public config

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/v1/config` | CLI bootstrap: public `apiUrl`, Zitadel `issuer`, and `clientId` |

No authentication and no database access. The response contains only public
OAuth values; never a client secret, token, or server setting. It is cached for
five minutes and exists so `secria login` can discover a self-hosted instance
from one URL. `clientId` is `ZITADEL_CLI_CLIENT_ID` when that is set, otherwise
`ZITADEL_CLIENT_ID`, so the web app and CLI can use separate Zitadel apps.

## Auth

| Method | Path | Purpose |
| --- | --- | --- |
| GET/POST | `/auth/login` | Start Zitadel PKCE login; optional `next`, `login_hint`, `prompt` |
| POST | `/auth/signup` | Same flow with `prompt=create` |
| GET | `/auth/callback` | Exchange the code, verify the ID token, set the session |
| POST | `/auth/logout` | Delete the local session and return `{logoutUrl}` |

The browser uses the HttpOnly `secria_session` cookie. CLI requests use
`Authorization: Bearer <jwt>`; CI uses `Authorization: Bearer secria_st_...`
(service token). An invalid Authorization header never falls back to the cookie.

## Me

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/v1/me` | Current user |
| PATCH | `/v1/me` | Update `{ "name": "..." }` |
| GET | `/v1/me/sessions` | List active web sessions |
| DELETE | `/v1/me/sessions/{id}` | Revoke one session |

## Workspaces

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/v1/workspaces` | Workspaces the caller belongs to |
| POST | `/v1/workspaces` | Create a workspace (caller becomes owner) |
| GET | `/v1/workspaces/{workspaceId}` | Workspace detail |
| PATCH | `/v1/workspaces/{workspaceId}` | Rename or change slug (owner/admin) |
| GET | `/v1/workspaces/{workspaceId}/members` | Members + project grants |
| PATCH | `/v1/workspaces/{workspaceId}/members/{userId}` | Change role |
| DELETE | `/v1/workspaces/{workspaceId}/members/{userId}` | Remove member |

Owner protections: a workspace always keeps at least one owner; only an owner
can manage owners.

## Projects

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/v1/workspaces/{workspaceId}/projects` | Accessible projects |
| POST | `/v1/workspaces/{workspaceId}/projects` | Create project (workspace owner/admin) |
| GET | `/v1/projects/{projectId}` | Project detail + accessible environments |
| PATCH | `/v1/projects/{projectId}` | Rename, re-slug, describe, archive |
| DELETE | `/v1/projects/{projectId}` | Delete project (project admin) |
| GET | `/v1/projects/{projectId}/environments` | Accessible environments |
| POST | `/v1/projects/{projectId}/environments` | Add environment (project admin) |
| GET | `/v1/projects/{projectId}/members` | Explicit members + implicit workspace admins |
| PUT | `/v1/projects/{projectId}/members/{userId}` | Grant/update role + environment restrictions |
| DELETE | `/v1/projects/{projectId}/members/{userId}` | Remove project grant |

A new project gets `dev`, `staging`, and `prod`, plus a wrapped project DEK, in
one transaction. A project member with no `project_member_envs` rows can access
every environment; with rows, only those environment IDs.

## Secrets

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/v1/projects/{projectId}/environments/{environmentId}/secrets` | Masked key list |
| PUT | `/v1/projects/{projectId}/environments/{environmentId}/secrets` | Bulk upsert (`merge` or `replace`) |
| GET | `/v1/projects/{projectId}/environments/{environmentId}/secrets/download?format=env\|json` | Plaintext download; audited |
| POST | `/v1/projects/{projectId}/environments/{environmentId}/secrets/diff` | Compare local keys + SHA-256 hashes |
| GET | `/v1/projects/{projectId}/environments/{environmentId}/secrets/{key}` | Reveal one value; audited |
| DELETE | `/v1/projects/{projectId}/environments/{environmentId}/secrets/{key}` | Soft delete; audited |
| GET | `/v1/projects/{projectId}/environments/{environmentId}/secrets/{key}/versions` | Version metadata |
| POST | `/v1/projects/{projectId}/environments/{environmentId}/secrets/{key}/rollback` | New version from an old plaintext |

- Keys must match `^[A-Z_][A-Z0-9_]*$` and be at most 200 characters.
- Bulk upsert is transactional and capped at 1000 keys and 64 KB per value.
- `replace` soft-deletes keys missing from the payload; `merge` leaves them.
- Unchanged values do not create a new version. Updates and restores do.
- Rollback creates a new version; it does not re-point history.
- Download format `env` quotes values that need it; `json` returns an object.
- Diff accepts `{ "secrets": [{ "key": "A", "valueSha256": "..." }] }` and
  returns `added`, `changed`, `removed`, and `unchanged` key lists.
- Every secrets response and audit response is `Cache-Control: no-store`; so is
  every service-token response.

## Audit log

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/v1/workspaces/{workspaceId}/audit-logs` | Filterable audit page |

Query parameters: `project` (UUID), `actor` (actor id or email), `action`
(exact), `cursor` (last item id), `limit` (1–100, default 50). Only workspace
owners/admins can read the audit log. Metadata contains key names, counts, and
roles, never secret values.

## Invites

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/v1/workspaces/{workspaceId}/invites` | Create + email an invite |
| GET | `/v1/workspaces/{workspaceId}/invites` | List invites and statuses |
| PATCH | `/v1/workspaces/{workspaceId}/invites/{inviteId}` | Change role or project grants |
| POST | `/v1/workspaces/{workspaceId}/invites/{inviteId}/resend` | Rotate the token and resend |
| DELETE | `/v1/workspaces/{workspaceId}/invites/{inviteId}` | Revoke |
| GET | `/v1/invites/{token}` | Preview for the matching signed-in email |
| POST | `/v1/invites/{token}/accept` | Accept and create memberships |

- Invite tokens are random, shown once in the email/create response, and stored
  only as SHA-256 hashes. Resend rotates the token.
- Invites expire after 7 days. Expired/revoked/accepted invites cannot be used.
- Only a workspace owner can invite another owner.
- Acceptance requires a signed-in user whose verified email matches the invite.
- Existing higher workspace/project roles are preserved on acceptance.
- The email is best-effort; the create/resend response always includes
  `inviteUrl` so an admin can share it manually when email is not configured.

## Service tokens

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/v1/service-tokens/current` | Resolve the caller service token's scope |
| GET | `/v1/projects/{projectId}/environments/{environmentId}/service-tokens` | List tokens (project admin) |
| POST | `/v1/projects/{projectId}/environments/{environmentId}/service-tokens` | Create a token (project admin) |
| DELETE | `/v1/projects/{projectId}/environments/{environmentId}/service-tokens/{tokenId}` | Revoke a token (project admin) |

- Tokens start with `secria_st_`; only the SHA-256 hash is stored, and the
  plaintext appears once in the create response.
- A token is scoped to exactly one project and environment. Requests for any
  other project or environment return 404; write requests with a `read` token
  return 403.
- Service tokens can use the secrets list/reveal/download/diff endpoints and,
  with `read_write`, bulk upsert, delete, and rollback. They cannot use `/me`,
  workspace/project/member routes, or create/revoke tokens.
- `GET /v1/service-tokens/current` returns workspace/project/environment IDs and
  slugs so the CLI can resolve a context without a user session.
- Creation and revocation are audited with `actorType: "service_token"` on
  secret actions and `service_token.created` / `service_token.revoked` events.

## Path convention

API paths use UUIDs. Slugs are unique per workspace (or per project for
environments), so the web app and CLI resolve a slug through the list endpoints
before calling a detail route. The UI route can still use readable slugs:
`/w/acme/p/api?env=production`.

## Roles

- Workspace: `owner`, `admin`, `member`.
- Project: `admin`, `editor`, `viewer`.
- Workspace owners/admins are implicit project admins and see every project.
- Members see only projects with a grant.
- Missing or invisible resources return **404**; visible resources with
  insufficient role return **403**.

## Status

All planned phases are implemented: API, dashboard, CLI, invites, service
tokens, and hardening. See `AGENTS.md` for the phase log.
