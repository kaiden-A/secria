import contextlib
import hashlib
import os
import re
import stat
from pathlib import Path

from dotenv import dotenv_values

from .errors import CliError

SAFE_VALUE = re.compile(r"[A-Za-z0-9_./:@%+,=-]+")


def parse_env(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise CliError(f"Env file not found: {path}")
    values = dotenv_values(path, interpolate=False)
    return {
        str(key): (value if value is not None else "")
        for key, value in values.items()
        if key is not None
    }


def hashes(values: dict[str, str]) -> dict[str, str]:
    return {
        key: hashlib.sha256(value.encode("utf-8")).hexdigest()
        for key, value in values.items()
    }


def payload(values: dict[str, str]) -> list[dict[str, str]]:
    return [{"key": key, "value": value} for key, value in values.items()]


def format_env(values: dict[str, str]) -> str:
    lines = [f"{key}={_quote(value)}" for key, value in sorted(values.items())]
    return "\n".join(lines) + ("\n" if lines else "")


def _quote(value: str) -> str:
    if value == "":
        return '""'
    if not value.startswith("#") and SAFE_VALUE.fullmatch(value):
        return value
    escaped = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
    )
    return f'"{escaped}"'


def write_env(path: Path, text: str) -> None:
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


def is_gitignored(path: Path) -> bool:
    target = path.resolve()
    for directory in (target.parent, *target.parent.parents):
        candidate = directory / ".gitignore"
        if not candidate.is_file():
            continue
        try:
            lines = candidate.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        patterns = {line.strip() for line in lines if line.strip() and not line.strip().startswith("#")}
        if target.name in patterns or ".env*" in patterns or "*.env" in patterns:
            return True
        if target.name.startswith(".env") and ".env" in patterns:
            return True
        # A directory-level ignore for the file's exact relative path.
        try:
            relative = target.relative_to(directory).as_posix()
        except ValueError:
            relative = target.name
        if relative in patterns:
            return True
    return False
