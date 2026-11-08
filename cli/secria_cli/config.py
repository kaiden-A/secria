import contextlib
import json
import os
import re
import stat
from io import StringIO
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import platformdirs
from dotenv import dotenv_values
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from .errors import CliError

REPO_ROOT = Path(__file__).resolve().parents[2]
LINK_NAME = ".secria.yaml"

# Hosted Secria API. Override with --server, SECRIA_API_URL, or `secria config set`.
DEFAULT_API_URL = "https://elysiaa-secria-server-1023333674013.asia-southeast1.run.app"

# Only these keys are read from a local .env. The CLI must never pull the
# server's database URL, master key, Resend key, or app secret into its process
# (and therefore into `secria run` subprocesses).
ALLOWED_ENV_KEYS = {
    "SECRIA_API_URL",
    "SECRIA_ZITADEL_ISSUER",
    "SECRIA_ZITADEL_CLIENT_ID",
    "ZITADEL_ISSUER",
    "ZITADEL_CLIENT_ID",
}

SETTING_KEYS = {
    "api-url": "api_url",
    "zitadel-issuer": "zitadel_issuer",
    "zitadel-client-id": "zitadel_client_id",
}


def _source_checkout() -> bool:
    """True when running from the git checkout rather than an installed tool."""
    return (REPO_ROOT / "cli" / "pyproject.toml").is_file()


def load_environment() -> None:
    """Read only CLI-relevant keys from local .env files in a source checkout.

    An installed CLI deliberately ignores a project's .env: a repository must
    not be able to redirect authentication to another API or IdP. Installed
    users configure a server with --server, SECRIA_API_URL, `secria config`, or
    the committed .secria.yaml `server:` field.

    Real environment variables always win. This deliberately does not call
    load_dotenv(): a developer's root .env contains server secrets that must not
    leak into CLI subprocesses.
    """
    if not _source_checkout():
        return
    candidates = [Path.cwd() / ".env", REPO_ROOT / ".env"]
    seen: set[Path] = set()
    for candidate in candidates:
        if not candidate.is_file():
            continue
        try:
            resolved = candidate.resolve()
        except OSError:
            resolved = candidate
        if resolved in seen:
            continue
        seen.add(resolved)
        values = dotenv_values(candidate, interpolate=False)
        for key in ALLOWED_ENV_KEYS:
            if key not in os.environ and values.get(key):
                os.environ[key] = str(values[key])


def normalize_url(value: str) -> str:
    return value.strip().rstrip("/")


def is_local_url(value: str) -> bool:
    host = urlparse(value).hostname or ""
    return host in {"localhost", "127.0.0.1", "::1"}


def validate_server_url(value: str) -> str:
    value = normalize_url(value)
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise CliError("Server URL must start with https:// (or http://localhost).")
    return value


def host_from(server: str) -> str:
    return urlparse(server).netloc or "default"


def current_host() -> str:
    return host_from(api_url())


def _host_slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("_") or "default"


def token_service(host: str | None = None) -> str:
    return f"secria:{_host_slug(host or current_host())}"


def config_dir() -> Path:
    override = os.getenv("SECRIA_CONFIG_DIR")
    if override:
        return Path(override).expanduser()
    return Path(platformdirs.user_config_dir("secria", appauthor=False))


def settings_path() -> Path:
    return config_dir() / "config.json"


def credentials_path(host: str | None = None) -> Path:
    return config_dir() / f"credentials-{_host_slug(host or current_host())}.json"


def legacy_credentials_path() -> Path:
    """Single-server path used before tokens were keyed by host."""
    return config_dir() / "credentials.json"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def load_settings() -> dict[str, Any]:
    return _read_json(settings_path())


def save_settings(settings: dict[str, Any]) -> None:
    secure_write(settings_path(), json.dumps(settings, indent=2) + "\n")


def _setting(name: str) -> str:
    return str(load_settings().get(name) or "").strip()


def _link_server() -> str:
    _path, data = find_link()
    return str(data.get("server") or "").strip()


def resolve_server(explicit: str | None = None) -> str:
    """Resolve the server: flag -> env -> saved config -> link file -> default.

    Returns an empty string when nothing is configured so the caller can prompt.
    """
    candidate = (
        (explicit or "").strip()
        or os.getenv("SECRIA_API_URL", "").strip()
        or _setting("api_url")
        or _link_server()
        or DEFAULT_API_URL
    )
    return validate_server_url(candidate) if candidate else ""


def api_url() -> str:
    return resolve_server()


def api_url_source() -> str:
    if (os.getenv("SECRIA_API_URL") or "").strip():
        return "env"
    if _setting("api_url"):
        return "config"
    if _link_server():
        return "link"
    if DEFAULT_API_URL:
        return "default"
    return "unset"


def zitadel_issuer() -> str:
    return normalize_url(
        os.getenv("SECRIA_ZITADEL_ISSUER", "").strip()
        or os.getenv("ZITADEL_ISSUER", "").strip()
        or _setting("zitadel_issuer")
    )


def zitadel_client_id() -> str:
    return (
        os.getenv("SECRIA_ZITADEL_CLIENT_ID", "").strip()
        or os.getenv("ZITADEL_CLIENT_ID", "").strip()
        or _setting("zitadel_client_id")
    )


def zitadel_issuer_source() -> str:
    if (
        os.getenv("SECRIA_ZITADEL_ISSUER", "").strip()
        or os.getenv("ZITADEL_ISSUER", "").strip()
    ):
        return "env"
    return "config" if _setting("zitadel_issuer") else "unset"


def zitadel_client_id_source() -> str:
    if (
        os.getenv("SECRIA_ZITADEL_CLIENT_ID", "").strip()
        or os.getenv("ZITADEL_CLIENT_ID", "").strip()
    ):
        return "env"
    return "config" if _setting("zitadel_client_id") else "unset"


def save_server_config(server: str, issuer: str, client_id: str) -> None:
    settings = load_settings()
    settings.update(
        {
            "api_url": normalize_url(server),
            "zitadel_issuer": normalize_url(issuer),
            "zitadel_client_id": client_id.strip(),
        }
    )
    save_settings(settings)


def save_setting(key: str, value: str) -> None:
    if key not in SETTING_KEYS:
        allowed = ", ".join(SETTING_KEYS)
        raise CliError(f"Unknown setting '{key}'. Choose one of: {allowed}.")
    cleaned = value.strip()
    if key == "api-url":
        cleaned = validate_server_url(cleaned)
    elif key == "zitadel-issuer":
        cleaned = normalize_url(cleaned)
        parsed = urlparse(cleaned)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise CliError("Zitadel issuer must start with https://.")
    if not cleaned:
        raise CliError(f"{key} cannot be empty.")
    settings = load_settings()
    settings[SETTING_KEYS[key]] = cleaned
    save_settings(settings)


def _yaml() -> YAML:
    parser = YAML(typ="safe")
    parser.default_flow_style = False
    setattr(parser, "sort_base_mapping_type_on_output", False)  # noqa: B010
    parser.width = 4096
    return parser


def _load_link(text: str) -> dict[str, Any]:
    try:
        data = _yaml().load(text)
    except (YAMLError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def dump_yaml(data: Any) -> str:
    stream = StringIO()
    _yaml().dump(data, stream)
    return stream.getvalue()


def find_link(start: Path | None = None) -> tuple[Path | None, dict[str, Any]]:
    current = (start or Path.cwd()).resolve()
    for directory in (current, *current.parents):
        candidate = directory / LINK_NAME
        if candidate.is_file():
            try:
                text = candidate.read_text(encoding="utf-8")
            except OSError:
                return candidate, {}
            return candidate, _load_link(text)
    return None, {}


def save_link(
    path: Path,
    *,
    workspace: str,
    project: str,
    environment: str,
    server: str | None = None,
) -> None:
    body: dict[str, str] = {
        "workspace": workspace,
        "project": project,
        "environment": environment,
    }
    if server:
        body["server"] = normalize_url(server)
    stream = StringIO()
    _yaml().dump(body, stream)
    text = (
        "# Secria link file. Safe to commit: it contains no secrets.\n"
        + stream.getvalue()
    )
    secure_write(path, text)


def secure_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    mode = stat.S_IRUSR | stat.S_IWUSR
    fd = os.open(path, flags, mode)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
    finally:
        with contextlib.suppress(OSError):
            os.chmod(path, mode)
