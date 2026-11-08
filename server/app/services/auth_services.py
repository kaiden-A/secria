from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DbSession

from ..config import Settings
from ..models import Session as SessionRow
from ..models import User
from ..schemas.users import PublicUser, SessionOut
from ..utils import to_ms
from . import security
from .errors import ConflictError, ForbiddenError, InvalidError, NotFoundError, UnauthorizedError
from .zitadel import ZitadelClient, ZitadelError

LAST_USED_THROTTLE = timedelta(minutes=5)


def _now() -> datetime:
    return datetime.now(UTC)


def _email_verified(claims: dict[str, Any]) -> bool:
    value = claims.get("email_verified")
    return value is True or value == 1 or (isinstance(value, str) and value.lower() == "true")


def _identity_from_claims(claims: dict[str, Any]) -> tuple[str, str, str]:
    subject = claims.get("sub")
    if not subject:
        raise UnauthorizedError("Your identity provider did not return a subject.")
    email = str(claims.get("email") or "").strip().lower()
    if not email:
        raise UnauthorizedError("Your identity provider did not return an email address.")
    if len(email) > 320:
        raise UnauthorizedError("Your email address is too long.")
    if not _email_verified(claims):
        raise ForbiddenError("Your email address must be verified before you can sign in.")
    name = str(claims.get("name") or claims.get("preferred_username") or email.split("@")[0]).strip()
    return str(subject)[:200], email, (name or "User")[:200]


def upsert_user_from_claims(db: DbSession, claims: dict[str, Any]) -> User:
    """Just-in-time provisioning from verified IdP claims."""
    subject, email, name = _identity_from_claims(claims)
    now = _now()

    user = db.scalar(select(User).where(User.zitadel_sub == subject))
    if user is not None:
        if user.email != email:
            owner = db.scalar(
                select(User).where(func.lower(User.email) == email, User.id != user.id)
            )
            if owner is not None:
                raise ConflictError("That email is already linked to another sign-in.")
            user.email = email
        if name and user.name != name:
            user.name = name
        user.last_login_at = now
        db.commit()
        return user

    # An invited person may already have a placeholder row with a null subject.
    existing = db.scalar(select(User).where(func.lower(User.email) == email))
    if existing is not None:
        if existing.zitadel_sub is not None:
            raise ConflictError("That email is already linked to another sign-in.")
        existing.zitadel_sub = subject
        existing.name = name
        existing.last_login_at = now
        db.commit()
        return existing

    user = User(zitadel_sub=subject, email=email, name=name, last_login_at=now)
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raced = db.scalar(select(User).where(User.zitadel_sub == subject))
        if raced is not None:
            return raced
        raise ConflictError("That email is already linked to another sign-in.") from exc
    return user


def user_from_bearer(db: DbSession, token: str, zitadel: ZitadelClient) -> User:
    try:
        claims = zitadel.verify_bearer(token)
    except ZitadelError as exc:
        raise UnauthorizedError("Your sign-in token is invalid or expired.") from exc
    return upsert_user_from_claims(db, claims)


def create_session(
    db: DbSession,
    user: User,
    *,
    settings: Settings,
    user_agent: str | None = None,
    ip: str | None = None,
) -> str:
    """Create a server-side session and return the raw cookie token."""
    token = security.new_session_token()
    now = _now()
    expires = now + timedelta(days=settings.session_ttl_days)
    db.add(
        SessionRow(
            user_id=user.id,
            token_hash=security.hash_token(token),
            kind="web",
            expires_at=expires,
            created_at=now,
            last_used_at=now,
            ip=(ip or "")[:64] or None,
            user_agent=(user_agent or "")[:500] or None,
        )
    )
    user.last_login_at = now
    db.commit()
    return token


def session_user(db: DbSession, token: str | None, *, settings: Settings) -> User | None:
    if not token:
        return None
    now = _now()
    row = db.scalar(select(SessionRow).where(SessionRow.token_hash == security.hash_token(token)))
    if row is None:
        return None
    if row.expires_at <= now:
        db.delete(row)
        db.commit()
        return None
    user = db.get(User, row.user_id)
    if user is None:
        db.delete(row)
        db.commit()
        return None

    dirty = False
    ttl = timedelta(days=settings.session_ttl_days)
    if row.expires_at - now < ttl / 2:
        row.expires_at = now + ttl
        dirty = True
    if row.last_used_at is None or now - row.last_used_at > LAST_USED_THROTTLE:
        row.last_used_at = now
        dirty = True
    if dirty:
        db.commit()
    return user


def revoke_session(db: DbSession, token: str | None) -> None:
    if not token:
        return
    row = db.scalar(select(SessionRow).where(SessionRow.token_hash == security.hash_token(token)))
    if row is not None:
        db.delete(row)
        db.commit()


def list_sessions(db: DbSession, user: User, *, current_token_hash: str | None) -> list[SessionOut]:
    rows = db.scalars(
        select(SessionRow)
        .where(SessionRow.user_id == user.id)
        .order_by(SessionRow.created_at.desc())
    ).all()
    return [
        SessionOut(
            id=str(row.id),
            kind=row.kind,
            createdAt=int(to_ms(row.created_at) or 0),
            lastUsedAt=to_ms(row.last_used_at),
            expiresAt=int(to_ms(row.expires_at) or 0),
            ip=row.ip,
            userAgent=row.user_agent,
            current=row.token_hash == current_token_hash,
        )
        for row in rows
    ]


def revoke_session_by_id(db: DbSession, user: User, session_id: UUID) -> SessionRow:
    row = db.get(SessionRow, session_id)
    if row is None or row.user_id != user.id:
        raise NotFoundError("Session not found.")
    db.delete(row)
    db.commit()
    return row


def update_name(db: DbSession, user: User, name: str) -> User:
    clean = name.strip()
    if not clean:
        raise InvalidError("A name is required.")
    user.name = clean[:200]
    db.commit()
    return user


def public_user(user: User) -> PublicUser:
    return PublicUser(
        id=str(user.id),
        name=user.name or "User",
        email=user.email,
        lastLoginAt=to_ms(user.last_login_at),
    )
