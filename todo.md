# Secria CLI distribution — decisions & TODO

Last updated: 2026-11-08

## Status

Phase 0 is implemented and tested locally. The public config endpoint is **not
live on Cloud Run yet**; deploy `server/**` to enable `secria login` discovery
against the hosted API.

## Locked decisions

| Area | Decision |
| --- | --- |
| Distribution order | PyPI first, npm wrapper second |
| PyPI project | `secria` (renamed from `secria-cli`) |
| Import package | `secria_cli` (unchanged) |
| Version | `0.1.0` |
| License | MIT |
| Python | `>=3.12` |
| Build backend | Hatchling |
| Entry point | `secria = "secria_cli.main:app"` |
| Default server | `https://elysiaa-secria-server-1023333674013.asia-southeast1.run.app` |
| Server override | `--server`, `SECRIA_API_URL`, saved config, `.secria.yaml` `server` |
| Discovery | Public `GET /api/v1/config` (`apiUrl`, `issuer`, `clientId`) |
| Login | Zitadel Device Authorization Grant (browser opens, code pre-filled) |
| Tokens | OS keychain, keyed per host (`secria:<host>`), `0600` file fallback |
| YAML | `ruamel.yaml` (pure Python; PyYAML has no cp315 wheels) |
| PyPI publishing | Trusted publishing (GitHub OIDC), no long-lived token |
| npm | PyInstaller `--onedir` binaries via `optionalDependencies` |
| npm install scripts | No `postinstall` network downloads |
| Release approval | Never publish to PyPI or npm without explicit approval |

### Do not

- Do not run `uv init --package secria` or `uv add` in this repo.
- Do not rename the `secria_cli` module as part of publishing.
- Do not restructure `main.py` before `0.1.0` ships.
- Do not bake `localhost` as the public default server.
- Do not read auth endpoints from a project `.env` in installed builds.
- Do not publish while the repo has no license or the CLI has no README.

## Phase 0 — done

### Server

- [x] Add `server/app/routers/config_router.py` with public `GET /api/v1/config`.
- [x] Register the router in `server/app/main.py`.
- [x] Return only `apiUrl`, `issuer`, `clientId`; cache for five minutes.
- [x] Fall back to the request origin when `API_BASE_URL` is localhost.
- [x] Add `server/tests/test_config.py`.
- [x] Document the endpoint in `docs/api.md`.

### CLI

- [x] Config precedence: flag → env → saved config → link file → default.
- [x] Guard `REPO_ROOT` in installed builds; ignore project `.env` for auth.
- [x] Add `secria config show|set|path`.
- [x] Add `secria doctor` (config, keyring, auth, link, API health, discovery).
- [x] Add `secria login --server URL` with discovery and saved config.
- [x] Keyring and file fallback scoped per server host.
- [x] Add global `--version` (keep `secria version`).
- [x] Add `cli/secria_cli/__main__.py`.
- [x] Rename the PyPI project to `secria`; add README, LICENSE, metadata.
- [x] Replace PyYAML with `ruamel.yaml` so installs work on Python 3.15.
- [x] Add `server:` to `.secria.yaml` on `init` / project creation.
- [x] Update root README, `cli/README.md`, and `AGENTS.md`.
- [x] `uv build --no-sources` succeeds; wheel contains code, README, LICENSE.
- [x] `uv tool install <wheel>` works on Python 3.12 and 3.15.
- [x] `secria --version`, `config show`, `doctor --offline` smoke-tested.
- [x] Local `GET /api/v1/config` verified with `secria doctor` discovery.
- [x] CLI tests, ruff, pyright, and all server tests pass.

### Deploy checklist

- [ ] Push `server/**` to `main` so CD deploys the new endpoint.
- [ ] Confirm Cloud Run has `ZITADEL_ISSUER`/`ZITADEL_CLIENT_ID` for the native
      app with the device grant enabled.
- [ ] Verify `GET https://<cloud-run-url>/api/v1/config` from outside.
- [ ] Run `secria login --server <cloud-run-url>` against the deployed API.
- [ ] Decide the final custom domain; then update `DEFAULT_API_URL`.
- [ ] Set `API_BASE_URL` to the custom domain (optional; request origin works).

## Phase 1 — PyPI

- [ ] Create PyPI account + 2FA; configure a pending trusted publisher for
      `kaiden-A/secria`, workflow `release-cli.yml`, environment `pypi`.
- [x] Add `.github/workflows/release-cli.yml` on `cli-v*` tags.
- [x] Build with `uv build --directory cli --no-sources`.
- [x] Smoke-install the wheel locally on Python 3.12 and 3.15.
- [ ] Push the workflow and let it smoke-install on Ubuntu, Windows, macOS.
- [ ] Publish with `uv publish` and `id-token: write`.
- [ ] Verify `uv tool install secria`, `uvx secria`, upgrade, uninstall.
- [ ] Do not publish without explicit approval.

## Phase 2 — npm wrapper

- [ ] PyInstaller `--onedir` spec; include keyring backend metadata.
- [ ] Build matrix: `windows-latest`, `macos-13`, `macos-15`, `ubuntu-22.04`.
- [ ] Platform packages gated by `os`/`cpu`/`libc`, `preferUnplugged: true`.
- [ ] `bin/secria.js` launcher; spawn and forward the exit code.
- [ ] Exact version pins; no `postinstall` download.
- [ ] Test with `npm ci --ignore-scripts` and `--omit=optional`.
- [ ] Publish platform packages first, wrapper last; `next` tag then `latest`.
- [ ] Verify `npm i -g secria` and `npx secria`.

## Phase 3 — later

- [ ] Loopback OAuth (PKCE, 127.0.0.1, state, device-flow fallback).
- [ ] Windows Authenticode signing.
- [ ] macOS Developer ID + notarization.
- [ ] Homebrew tap, Scoop bucket, winget.
- [ ] Refactor `main.py` into `commands/` + `core/` after 0.1.0.
- [ ] Multi-instance profile display in `config show`.
- [ ] Decide whether to publish a scoped `@secria/cli` alias.

## Open questions

- [ ] Final custom domain for the Cloud Run API.
- [ ] MIT copyright holder (currently `Kaiden-A`).
- [ ] PyPI/npm account owners and 2FA devices.
- [ ] Whether the public package should default to the hosted API or prompt.
