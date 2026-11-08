"""Outbound email through Resend.

One choke point: deliver() takes already-rendered HTML and text. With no API key
configured, mail is rendered and logged instead of sent, so local development
does not need Resend. Invite tokens are never logged.
"""

import logging
from pathlib import Path

import httpx
from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..config import get_settings
from ..models import Invite, User, Workspace

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
RESEND_ENDPOINT = "https://api.resend.com/emails"

_env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(["html", "xml"]),
    trim_blocks=True,
    lstrip_blocks=True,
)


def render(template: str, context: dict[str, object]) -> str:
    return _env.get_template(template).render(**context)


def _deliver(*, to: str, subject: str, html: str, text: str) -> str | None:
    """The network seam; tests monkeypatch this."""
    settings = get_settings()
    payload: dict[str, object] = {
        "from": settings.email_from,
        "to": [to],
        "subject": subject,
        "html": html,
        "text": text,
    }
    if settings.email_reply_to:
        payload["reply_to"] = settings.email_reply_to
    response = httpx.post(
        RESEND_ENDPOINT,
        json=payload,
        headers={"Authorization": f"Bearer {settings.resend_api_key}"},
        timeout=15.0,
    )
    response.raise_for_status()
    return str(response.json().get("id") or "")


def send_invite(
    *,
    invite: Invite,
    workspace: Workspace,
    inviter: User,
    grants: list[dict[str, str]],
    invite_url: str,
) -> bool:
    """Render and best-effort send the invite. Never raises.

    Returns True when the provider accepted the message. The invite itself is
    already committed before this runs, so a mail failure never loses the invite.
    """
    settings = get_settings()
    subject = f"{inviter.name or 'A teammate'} invited you to {workspace.name} on Secria"
    context: dict[str, object] = {
        "subject": subject,
        "workspace_name": workspace.name,
        "workspace_slug": workspace.slug,
        "inviter_name": inviter.name or "A teammate",
        "inviter_email": inviter.email,
        "invite_url": invite_url,
        "role": invite.role.value,
        "grants": grants,
        "expires_at": invite.expires_at,
    }
    html = render("emails/invite.html", context)
    text = render("emails/invite.txt", context)
    recipient = settings.email_override_to.strip() or invite.email
    if not recipient:
        return False
    if not settings.resend_api_key:
        logger.info("invite email rendered but not sent (no RESEND_API_KEY) for %s", invite.email)
        return False
    try:
        _deliver(to=recipient, subject=subject, html=html, text=text)
    except httpx.HTTPError as exc:
        logger.warning("invite email failed for %s (%s)", invite.email, type(exc).__name__)
        return False
    return True
