import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session as DbSession

from ..models import AuditLog, User
from ..schemas.audit import AuditLogOut, AuditLogPage
from ..utils import to_ms
from .errors import InvalidError
from .permissions import require_workspace_admin


@dataclass(frozen=True)
class AuditContext:
    ip: str | None = None
    user_agent: str | None = None


def record(
    db: DbSession,
    *,
    workspace_id: uuid.UUID,
    action: str,
    target: str,
    actor: User | None = None,
    actor_type: str = "user",
    actor_id: str | None = None,
    project_id: uuid.UUID | None = None,
    environment_id: uuid.UUID | None = None,
    metadata: dict[str, Any] | None = None,
    context: AuditContext | None = None,
) -> AuditLog:
    """Add an audit row to the caller's transaction.

    Callers commit with the action they are auditing. Metadata contains key
    names, counts, and roles; never plaintext values.
    """
    log = AuditLog(
        workspace_id=workspace_id,
        project_id=project_id,
        environment_id=environment_id,
        actor_type=actor_type,
        actor_id=actor_id or (str(actor.id) if actor is not None else None),
        action=action[:64],
        target=target[:320],
        meta=metadata or {},
        ip=(context.ip[:64] if context and context.ip else None),
        user_agent=(context.user_agent[:500] if context and context.user_agent else None),
    )
    db.add(log)
    return log


def _actor_map(db: DbSession, logs: list[AuditLog]) -> dict[uuid.UUID, User]:
    actor_ids: set[uuid.UUID] = set()
    for log in logs:
        if log.actor_type != "user" or not log.actor_id:
            continue
        try:
            actor_ids.add(uuid.UUID(log.actor_id))
        except ValueError:
            continue
    if not actor_ids:
        return {}
    users = db.scalars(select(User).where(User.id.in_(actor_ids))).all()
    return {user.id: user for user in users}


def _audit_out(log: AuditLog, users: dict[uuid.UUID, User]) -> AuditLogOut:
    actor = None
    if log.actor_type == "user" and log.actor_id:
        try:
            actor = users.get(uuid.UUID(log.actor_id))
        except ValueError:
            actor = None
    return AuditLogOut(
        id=str(log.id),
        workspaceId=str(log.workspace_id),
        projectId=str(log.project_id) if log.project_id else None,
        environmentId=str(log.environment_id) if log.environment_id else None,
        actorType=log.actor_type,
        actorId=log.actor_id,
        actorName=actor.name if actor else None,
        actorEmail=actor.email if actor else None,
        action=log.action,
        target=log.target,
        metadata=log.meta,
        ip=log.ip,
        userAgent=log.user_agent,
        createdAt=int(to_ms(log.created_at) or 0),
    )


def list_audit_logs(
    db: DbSession,
    user: User,
    workspace_id: uuid.UUID,
    *,
    project_id: uuid.UUID | None = None,
    actor: str | None = None,
    action: str | None = None,
    cursor: str | None = None,
    limit: int = 50,
) -> AuditLogPage:
    require_workspace_admin(db, user, workspace_id)
    query = select(AuditLog).where(AuditLog.workspace_id == workspace_id)
    if project_id is not None:
        query = query.where(AuditLog.project_id == project_id)
    if actor:
        actor = actor.strip()
        if "@" in actor:
            actor_ids = db.scalars(
                select(User.id).where(func.lower(User.email) == actor.lower())
            ).all()
            query = query.where(AuditLog.actor_id.in_([str(actor_id) for actor_id in actor_ids]))
        else:
            query = query.where(AuditLog.actor_id == actor)
    if action:
        query = query.where(AuditLog.action == action.strip())
    if cursor:
        try:
            cursor_id = uuid.UUID(cursor)
        except ValueError as exc:
            raise InvalidError("Invalid audit cursor.") from exc
        last = db.get(AuditLog, cursor_id)
        if last is None or last.workspace_id != workspace_id:
            raise InvalidError("Invalid audit cursor.")
        query = query.where(
            or_(
                AuditLog.created_at < last.created_at,
                and_(AuditLog.created_at == last.created_at, AuditLog.id < last.id),
            )
        )
    rows = list(
        db.scalars(
            query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).limit(limit + 1)
        ).all()
    )
    has_more = len(rows) > limit
    rows = rows[:limit]
    next_cursor = str(rows[-1].id) if has_more and rows else None
    users = _actor_map(db, rows)
    return AuditLogPage(
        items=[_audit_out(log, users) for log in rows],
        nextCursor=next_cursor,
    )
