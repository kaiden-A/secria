# Secria CLI

Push, pull, diff, and run with secrets from a
[Secria](https://github.com/kaiden-A/secria) server.

## Install

```bash
uv tool install secria
```

Or with pipx:

```bash
pipx install secria
```

Run it once without a permanent install:

```bash
uvx secria --help
```

Upgrade or remove it:

```bash
uv tool upgrade secria
uv tool uninstall secria
```

## Quick start

```bash
secria login                 # opens the browser for the Zitadel device flow
secria init                  # link this directory to a workspace/project/environment
secria pull --env dev        # write .env
secria push .env --env dev   # compare hashes, then upload
secria run --env dev -- npm start
```

`pull` refuses to overwrite an existing file without `--force`. `run` injects
secrets in memory and never writes a `.env`.

## Self-hosted servers

`secria login` uses the hosted API by default. For another instance, pass the
server URL once:

```bash
secria login --server https://secria.example.com
```

The CLI reads the public `/api/v1/config` endpoint for the Zitadel issuer and
client ID, so users never type those values. The server URL is saved locally;
later commands need no flags. A committed `.secria.yaml` may also carry a
`server:` value for teammates, but `--server` and `SECRIA_API_URL` win.

## Configuration

Settings are stored in the platform config directory:

- Windows: `%LOCALAPPDATA%\secria\config.json`
- macOS: `~/Library/Application Support/secria/config.json`
- Linux: `~/.config/secria/config.json`

Precedence: command flag, environment variable, saved config, link file,
built-in default. An installed CLI does **not** read authentication endpoints
from a project `.env`; a source checkout does, for local development.

```bash
secria config show
secria config set api-url https://secria.example.com
secria config set zitadel-issuer https://auth.example.com
secria config set zitadel-client-id 123456789
secria config path
secria doctor
```

`doctor` prints the resolved settings, keyring backend, session state, link
file, and API health. It never prints tokens.

## Authentication

- Browser login uses the Zitadel Device Authorization Grant. The CLI opens the
  verification page with the code pre-filled and polls until you approve.
- Sessions live in the OS keychain (Windows Credential Manager, macOS Keychain,
  or Secret Service on Linux), with a mode `0600` file fallback.
- Entries are scoped per server host, so two self-hosted instances do not
  overwrite each other.
- Set `SECRIA_TOKEN` to a service token (`secria_st_...`) for CI. Service tokens
  are project/environment-scoped and bypass the browser.
- Set `SECRIA_DISABLE_KEYRING=1` to force the file fallback.

## Development

From the monorepo:

```bash
cd cli
uv sync
uv run secria --help
uv run pytest
uv run ruff check .
uv run pyright
```

Install the working tree as a global tool:

```bash
cd cli
uv tool install --editable .
```

## Security

- The CLI only decrypts through the API; it never holds the server master key.
- `run` removes `SECRIA_TOKEN` from the child process environment.
- In a source checkout, the CLI reads only `SECRIA_API_URL`,
  `SECRIA_ZITADEL_*`, `ZITADEL_ISSUER`, and `ZITADEL_CLIENT_ID` from a local
  `.env`; server secrets are never loaded. Installed builds ignore project
  `.env` files for these values.
- Use HTTPS for remote servers. `secria login` warns when a non-local server
  uses plain HTTP.
