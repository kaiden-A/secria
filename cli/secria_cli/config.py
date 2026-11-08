import contextlib
import json
import os
import stat
from pathlib import Path
from typing import Any

import platformdirs
import yaml
from dotenv import dotenv_values

REPO_ROOT = Path(__file__).resolve().parents[2]
LINK_NAME = ".secria.yaml"

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


def load_environment() -> None:
    """Read only CLI-relevant keys from local .env files.

    Real environment variables always win. This deliberately does not call
    load_dotenv(): a developer's root .env contains server secrets that must not
    leak into CLI subprocesses.
    """
    for candidate in (Path.cwd() / ".env", REPO_ROOT / ".env"):
        if not candidate.is_file():
            continue
        values = dotenv_values(candidate, interpolate=False)
        for key in ALLOWED_ENV_KEYS:
            if key not in os.environ and values.get(key):
                os.environ[key] = str(values[key])


def api_url() -> str:
    return os.getenv("SECRIA_API_URL", "http://localhost:8000").rstrip("/")


def zitadel_issuer() -> str:
    return os.getenv("SECRIA_ZITADEL_ISSUER") or os.getenv("ZITADEL_ISSUER", "")


def zitadel_client_id() -> str:
    return os.getenv("SECRIA_ZITADEL_CLIENT_ID") or os.getenv("ZITADEL_CLIENT_ID", "")


def config_dir() -> Path:
    override = os.getenv("SECRIA_CONFIG_DIR")
    if override:
        return Path(override).expanduser()
    return Path(platformdirs.user_config_dir("secria", appauthor=False))


def credentials_path() -> Path:
    return config_dir() / "credentials.json"


def settings_path() -> Path:
    return config_dir() / "config.json"


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


def find_link(start: Path | None = None) -> tuple[Path | None, dict[str, Any]]:
    current = (start or Path.cwd()).resolve()
    for directory in (current, *current.parents):
        candidate = directory / LINK_NAME
        if candidate.is_file():
            try:
                data = yaml.safe_load(candidate.read_text(encoding="utf-8"))
            except (OSError, yaml.YAMLError):
                return candidate, {}
            return candidate, data if isinstance(data, dict) else {}
    return None, {}


def save_link(
    path: Path,
    *,
    workspace: str,
    project: str,
    environment: str,
) -> None:
    body = {
        "workspace": workspace,
        "project": project,
        "environment": environment,
    }
    text = (
        "# Secria link file. Safe to commit: it contains no secrets.\n"
        + yaml.safe_dump(body, sort_keys=False)
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
