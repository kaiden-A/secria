import re
import unicodedata

from .errors import InvalidError

SLUG_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    return slug[:63].rstrip("-")


def normalize_slug(value: str | None, *, fallback: str | None = None) -> str:
    slug = slugify((value or fallback or "").strip())
    if not slug or not SLUG_RE.match(slug):
        raise InvalidError(
            "Use a slug with lowercase letters, numbers and single hyphens (max 63 characters)."
        )
    return slug
