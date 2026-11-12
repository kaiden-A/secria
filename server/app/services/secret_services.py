import hashlib
import re
import uuid
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from ..dependencies import Principal
from ..models import Environment, ProjectKey, ProjectRole, Secret, SecretVersion, User, utcnow
from ..schemas.secrets import (
    BulkSecretInput,
    BulkUpsertRequest,
    BulkUpsertResult,
    CopySecretsRequest,
    DiffRequest,
    DiffResult,
    DiffSecretInput,
    RollbackRequest,
    SecretOut,
    SecretValueOut,
    SecretVersionOut,
)
from ..utils import to_ms
from . import audit_services, token_services
from .audit_services import AuditContext
from .encryption import (
    DecryptionError,
    decrypt_secret,
    encrypt_secret,
    get_master_key,
    secret_aad,
)
from .errors import InvalidError, NotFoundError, UnauthorizedError, UnavailableError
from .permissions import ProjectAccess, require_project_access

SECRET_KEY_RE = re.compile(r"^[A-Z_][A-Z0-9_]*$")
MAX_SECRETS = 1000
MAX_VALUE_BYTES = 64 * 1024
MAX_AUDIT_KEYS = 200


def _validate_key(raw: str) -> str:
    key = raw.strip()
    if not key or len(key) > 200 or not SECRET_KEY_RE.fullmatch(key):
        raise InvalidError("Secret keys must match ^[A-Z_][A-Z0-9_]*$ and be at most 200 characters.")
    return key


def _validate_value(value: str, key: str) -> None:
    if len(value.encode("utf-8")) > MAX_VALUE_BYTES:
        raise InvalidError(f"The value for {key} is larger than 64 KB.")


def _project_key(
    db: DbSession, project_id: uuid.UUID, key_version: int | None = None
) -> tuple[ProjectKey, bytes]:
    query = select(ProjectKey).where(ProjectKey.project_id == project_id)
    if key_version is not None:
        query = query.where(ProjectKey.key_version == key_version)
    key = db.scalar(query.order_by(ProjectKey.key_version.desc()).limit(1))
    if key is None:
        raise UnavailableError("Project encryption key is missing.")
    try:
        master = get_master_key()
    except (RuntimeError, ValueError) as exc:
        raise UnavailableError("Encryption is not configured.") from exc
    try:
        dek = master.unwrap_dek(
            key.encrypted_dek,
            project_id=project_id,
            key_version=key.key_version,
            kek_version=key.kek_version,
        )
    except DecryptionError as exc:
        raise UnavailableError("Project encryption key could not be opened.") from exc
    return key, dek


def _dek_for(
    db: DbSession,
    project_id: uuid.UUID,
    key_version: int,
    cache: dict[int, bytes],
) -> bytes:
    if key_version not in cache:
        _key, cache[key_version] = _project_key(db, project_id, key_version)
    return cache[key_version]


def _access(
    db: DbSession,
    principal: Principal,
    project_id: uuid.UUID,
    environment_id: uuid.UUID,
    *,
    roles: set[ProjectRole] | None = None,
) -> tuple[ProjectAccess, Environment]:
    if principal.service_token is not None:
        return token_services.require_service_access(
            db,
            principal.service_token,
            project_id,
            environment_id,
            write=roles is not None,
        )
    if principal.user is None:
        raise UnauthorizedError("A user session is required.")
    access = require_project_access(
        db,
        principal.user,
        project_id,
        roles=roles,
        environment_id=environment_id,
    )
    environment = db.get(Environment, environment_id)
    if environment is None or environment.project_id != access.project.id:
        raise NotFoundError("Environment not found.")
    return access, environment


def _record(
    db: DbSession,
    principal: Principal,
    access: ProjectAccess,
    environment: Environment,
    *,
    action: str,
    target: str,
    metadata: dict,
    context: AuditContext | None,
) -> None:
    audit_services.record(
        db,
        workspace_id=access.workspace.id,
        project_id=access.project.id,
        environment_id=environment.id,
        actor=principal.user,
        actor_type="user" if principal.user is not None else "service_token",
        actor_id=(
            str(principal.service_token.id)
            if principal.user is None and principal.service_token is not None
            else None
        ),
        action=action,
        target=target,
        metadata=metadata,
        context=context,
    )


def _current_version(db: DbSession, secret: Secret) -> SecretVersion | None:
    if secret.current_version_id is None:
        return None
    return db.get(SecretVersion, secret.current_version_id)


def _secret(db: DbSession, environment_id: uuid.UUID, key: str) -> Secret:
    secret = db.scalar(
        select(Secret).where(
            Secret.environment_id == environment_id,
            Secret.key == key,
            Secret.deleted_at.is_(None),
        )
    )
    if secret is None:
        raise NotFoundError("Secret not found.")
    return secret


def _secret_out(secret: Secret, version: SecretVersion | None) -> SecretOut:
    return SecretOut(
        key=secret.key,
        version=version.version if version else None,
        comment=version.comment if version else "",
        createdAt=int(to_ms(secret.created_at) or 0),
        updatedAt=int(to_ms(secret.updated_at) or 0),
    )


def _next_version(db: DbSession, secret_id: uuid.UUID) -> int:
    current = db.scalar(
        select(func.max(SecretVersion.version)).where(SecretVersion.secret_id == secret_id)
    )
    return (current or 0) + 1


def _decrypt_version(
    db: DbSession,
    access: ProjectAccess,
    environment: Environment,
    secret: Secret,
    version: SecretVersion,
    dek_cache: dict[int, bytes],
) -> str:
    dek = _dek_for(db, access.project.id, version.key_version, dek_cache)
    aad = secret_aad(
        workspace_id=access.workspace.id,
        project_id=access.project.id,
        environment_id=environment.id,
        key=secret.key,
    )
    try:
        return decrypt_secret(version.ciphertext, version.nonce, dek, aad=aad)
    except DecryptionError as exc:
        raise UnavailableError("A secret could not be decrypted.") from exc


def _audit_keys(keys: list[str]) -> list[str]:
    return keys[:MAX_AUDIT_KEYS]


def list_secrets(
    db: DbSession,
    principal: Principal,
    project_id: uuid.UUID,
    environment_id: uuid.UUID,
) -> list[SecretOut]:
    _access(db, principal, project_id, environment_id)
    rows = db.execute(
        select(Secret, SecretVersion)
        .outerjoin(SecretVersion, SecretVersion.id == Secret.current_version_id)
        .where(Secret.environment_id == environment_id, Secret.deleted_at.is_(None))
        .order_by(Secret.key)
    ).all()
    return [_secret_out(secret, version) for secret, version in rows]


def reveal_secret(
    db: DbSession,
    principal: Principal,
    project_id: uuid.UUID,
    environment_id: uuid.UUID,
    key: str,
    *,
    context: AuditContext | None = None,
) -> SecretValueOut:
    access, environment = _access(db, principal, project_id, environment_id)
    secret = _secret(db, environment.id, _validate_key(key))
    version = _current_version(db, secret)
    if version is None:
        raise NotFoundError("Secret value not found.")
    value = _decrypt_version(db, access, environment, secret, version, {})
    _record(
        db,
        principal,
        access,
        environment,
        action="secret.revealed",
        target=f"secret:{secret.key}",
        metadata={"version": version.version},
        context=context,
    )
    db.commit()
    return SecretValueOut(key=secret.key, value=value, version=version.version)


def download_secrets(
    db: DbSession,
    principal: Principal,
    project_id: uuid.UUID,
    environment_id: uuid.UUID,
    *,
    format: Literal["env", "json"],
    context: AuditContext | None = None,
) -> dict[str, str]:
    access, environment = _access(db, principal, project_id, environment_id)
    rows = db.execute(
        select(Secret, SecretVersion)
        .outerjoin(SecretVersion, SecretVersion.id == Secret.current_version_id)
        .where(Secret.environment_id == environment.id, Secret.deleted_at.is_(None))
        .order_by(Secret.key)
    ).all()
    dek_cache: dict[int, bytes] = {}
    values: dict[str, str] = {}
    for secret, version in rows:
        if version is None:
            raise UnavailableError("A secret has no current version.")
        values[secret.key] = _decrypt_version(db, access, environment, secret, version, dek_cache)
    _record(
        db,
        principal,
        access,
        environment,
        action="secret.downloaded",
        target=f"environment:{environment.slug}",
        metadata={
            "format": format,
            "count": len(values),
            "keys": _audit_keys(sorted(values)),
        },
        context=context,
    )
    db.commit()
    return values


def diff_secrets(
    db: DbSession,
    principal: Principal,
    project_id: uuid.UUID,
    environment_id: uuid.UUID,
    request: DiffRequest,
    *,
    context: AuditContext | None = None,
    source_environment: Environment | None = None,
) -> DiffResult:
    access, environment = _access(db, principal, project_id, environment_id)
    if len(request.secrets) > MAX_SECRETS:
        raise InvalidError("At most 1000 secrets can be compared at once.")
    local: dict[str, str | None] = {}
    for item in request.secrets:
        key = _validate_key(item.key)
        if key in local:
            raise InvalidError("Duplicate secret key in request.")
        digest = item.valueSha256.lower() if item.valueSha256 else None
        if digest is not None and not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise InvalidError("valueSha256 must be a 64-character hex digest.")
        local[key] = digest

    rows = db.execute(
        select(Secret, SecretVersion)
        .outerjoin(SecretVersion, SecretVersion.id == Secret.current_version_id)
        .where(Secret.environment_id == environment.id, Secret.deleted_at.is_(None))
        .order_by(Secret.key)
    ).all()
    dek_cache: dict[int, bytes] = {}
    remote: dict[str, str] = {}
    for secret, version in rows:
        if version is None:
            raise UnavailableError("A secret has no current version.")
        value = _decrypt_version(db, access, environment, secret, version, dek_cache)
        remote[secret.key] = hashlib.sha256(value.encode("utf-8")).hexdigest()

    added = sorted(set(local) - set(remote))
    removed = sorted(set(remote) - set(local))
    changed = sorted(
        key
        for key in set(local) & set(remote)
        if local[key] is None or local[key] != remote[key]
    )
    unchanged = sorted(
        key
        for key in set(local) & set(remote)
        if local[key] is not None and local[key] == remote[key]
    )
    metadata: dict = {
        "added": len(added),
        "changed": len(changed),
        "removed": len(removed),
        "unchanged": len(unchanged),
        "addedKeys": _audit_keys(added),
        "changedKeys": _audit_keys(changed),
        "removedKeys": _audit_keys(removed),
    }
    if source_environment is not None:
        metadata["sourceEnvironment"] = source_environment.slug
    _record(
        db,
        principal,
        access,
        environment,
        action="secret.diffed",
        target=f"environment:{environment.slug}",
        metadata=metadata,
        context=context,
    )
    db.commit()
    return DiffResult(
        added=added,
        changed=changed,
        removed=removed,
        unchanged=unchanged,
    )


def _decrypt_environment(
    db: DbSession,
    access: ProjectAccess,
    environment: Environment,
) -> list[BulkSecretInput]:
    rows = db.execute(
        select(Secret, SecretVersion)
        .outerjoin(SecretVersion, SecretVersion.id == Secret.current_version_id)
        .where(Secret.environment_id == environment.id, Secret.deleted_at.is_(None))
        .order_by(Secret.key)
    ).all()
    if len(rows) > MAX_SECRETS:
        raise InvalidError("At most 1000 secrets can be copied at once.")
    dek_cache: dict[int, bytes] = {}
    inputs: list[BulkSecretInput] = []
    for secret, version in rows:
        if version is None:
            raise UnavailableError("A secret has no current version.")
        value = _decrypt_version(db, access, environment, secret, version, dek_cache)
        inputs.append(
            BulkSecretInput(key=secret.key, value=value, comment=version.comment[:500])
        )
    return inputs


def _copy_environment(
    db: DbSession,
    principal: Principal,
    project_id: uuid.UUID,
    source_environment_id: uuid.UUID,
    target_environment_id: uuid.UUID,
    *,
    write: bool,
) -> tuple[Environment, list[BulkSecretInput]]:
    if principal.service_token is not None:
        raise UnauthorizedError("A user session is required.")
    source_access, source_environment = _access(
        db, principal, project_id, source_environment_id
    )
    if source_environment.id == target_environment_id:
        raise InvalidError("Choose a different environment.")
    _access(
        db,
        principal,
        project_id,
        target_environment_id,
        roles={ProjectRole.admin, ProjectRole.editor} if write else None,
    )
    return source_environment, _decrypt_environment(db, source_access, source_environment)


def preview_copy_secrets(
    db: DbSession,
    principal: Principal,
    project_id: uuid.UUID,
    environment_id: uuid.UUID,
    request: CopySecretsRequest,
    *,
    context: AuditContext | None = None,
) -> DiffResult:
    source_environment, inputs = _copy_environment(
        db,
        principal,
        project_id,
        request.sourceEnvironmentId,
        environment_id,
        write=False,
    )
    return diff_secrets(
        db,
        principal,
        project_id,
        environment_id,
        DiffRequest(
            secrets=[
                DiffSecretInput(
                    key=item.key,
                    valueSha256=hashlib.sha256(item.value.encode("utf-8")).hexdigest(),
                )
                for item in inputs
            ]
        ),
        context=context,
        source_environment=source_environment,
    )


def copy_secrets(
    db: DbSession,
    principal: Principal,
    project_id: uuid.UUID,
    environment_id: uuid.UUID,
    request: CopySecretsRequest,
    *,
    context: AuditContext | None = None,
) -> BulkUpsertResult:
    source_environment, inputs = _copy_environment(
        db,
        principal,
        project_id,
        request.sourceEnvironmentId,
        environment_id,
        write=True,
    )
    return bulk_upsert(
        db,
        principal,
        project_id,
        environment_id,
        BulkUpsertRequest(secrets=inputs, mode=request.mode),
        context=context,
        source_environment=source_environment,
    )


def bulk_upsert(
    db: DbSession,
    principal: Principal,
    project_id: uuid.UUID,
    environment_id: uuid.UUID,
    request: BulkUpsertRequest,
    *,
    context: AuditContext | None = None,
    source_environment: Environment | None = None,
) -> BulkUpsertResult:
    access, environment = _access(
        db,
        principal,
        project_id,
        environment_id,
        roles={ProjectRole.admin, ProjectRole.editor},
    )
    if len(request.secrets) > MAX_SECRETS:
        raise InvalidError("At most 1000 secrets can be written at once.")
    inputs: dict[str, BulkSecretInput] = {}
    for item in request.secrets:
        key = _validate_key(item.key)
        if key in inputs:
            raise InvalidError("Duplicate secret key in request.")
        _validate_value(item.value, key)
        inputs[key] = item

    active_key, active_dek = _project_key(db, access.project.id)
    dek_cache: dict[int, bytes] = {active_key.key_version: active_dek}
    all_secrets = {
        secret.key: secret
        for secret in db.scalars(
            select(Secret).where(Secret.environment_id == environment.id)
        ).all()
    }
    now = utcnow()
    created_keys: list[str] = []
    updated_keys: list[str] = []
    unchanged_keys: list[str] = []
    removed_keys: list[str] = []
    versions: dict[str, int] = {}

    for key, item in inputs.items():
        secret = all_secrets.get(key)
        if secret is None:
            secret_id = uuid.uuid4()
            secret = Secret(
                id=secret_id,
                environment_id=environment.id,
                key=key,
                created_at=now,
                updated_at=now,
            )
            db.add(secret)
            version_number = 1
            created_keys.append(key)
        elif secret.deleted_at is not None:
            secret.deleted_at = None
            secret.updated_at = now
            version_number = _next_version(db, secret.id)
            created_keys.append(key)
        else:
            current = _current_version(db, secret)
            if current is not None:
                aad = secret_aad(
                    workspace_id=access.workspace.id,
                    project_id=access.project.id,
                    environment_id=environment.id,
                    key=key,
                )
                try:
                    existing_value = decrypt_secret(
                        current.ciphertext,
                        current.nonce,
                        _dek_for(db, access.project.id, current.key_version, dek_cache),
                        aad=aad,
                    )
                except DecryptionError as exc:
                    raise UnavailableError("A secret could not be decrypted.") from exc
                if existing_value == item.value:
                    unchanged_keys.append(key)
                    versions[key] = current.version
                    continue
            version_number = _next_version(db, secret.id)
            secret.updated_at = now
            updated_keys.append(key)

        aad = secret_aad(
            workspace_id=access.workspace.id,
            project_id=access.project.id,
            environment_id=environment.id,
            key=key,
        )
        try:
            encrypted = encrypt_secret(item.value, active_dek, aad=aad)
        except ValueError as exc:
            raise UnavailableError("Encryption is not configured.") from exc
        version = SecretVersion(
            id=uuid.uuid4(),
            secret_id=secret.id,
            version=version_number,
            ciphertext=encrypted.ciphertext,
            nonce=encrypted.nonce,
            key_version=active_key.key_version,
            created_by=principal.user.id if principal.user is not None else None,
            created_at=now,
            comment=item.comment,
        )
        db.add(version)
        secret.current_version_id = version.id
        versions[key] = version_number

    if request.mode == "replace":
        for key, secret in all_secrets.items():
            if key in inputs or secret.deleted_at is not None:
                continue
            secret.deleted_at = now
            secret.updated_at = now
            removed_keys.append(key)

    result = BulkUpsertResult(
        added=len(created_keys),
        updated=len(updated_keys),
        removed=len(removed_keys),
        unchanged=len(unchanged_keys),
    )

    if (
        source_environment is None
        and request.mode == "merge"
        and len(inputs) == 1
        and not removed_keys
    ):
        key = next(iter(inputs))
        if key in created_keys:
            _record(
                db,
                principal,
                access,
                environment,
                action="secret.created",
                target=f"secret:{key}",
                metadata={"version": versions.get(key)},
                context=context,
            )
        elif key in updated_keys:
            _record(
                db,
                principal,
                access,
                environment,
                action="secret.updated",
                target=f"secret:{key}",
                metadata={"version": versions.get(key)},
                context=context,
            )
        else:
            _record(
                db,
                principal,
                access,
                environment,
                action="secret.bulk_upserted",
                target=f"environment:{environment.slug}",
                metadata={
                    "mode": request.mode,
                    "added": 0,
                    "updated": 0,
                    "removed": 0,
                    "unchanged": result.unchanged,
                    "unchangedKeys": _audit_keys(unchanged_keys),
                },
                context=context,
            )
    else:
        metadata: dict = {
            "mode": request.mode,
            "added": result.added,
            "updated": result.updated,
            "removed": result.removed,
            "unchanged": result.unchanged,
            "addedKeys": _audit_keys(created_keys),
            "updatedKeys": _audit_keys(updated_keys),
            "removedKeys": _audit_keys(removed_keys),
        }
        if source_environment is not None:
            metadata["sourceEnvironment"] = source_environment.slug
        _record(
            db,
            principal,
            access,
            environment,
            action=(
                "secret.copied"
                if source_environment is not None
                else "secret.bulk_upserted"
            ),
            target=f"environment:{environment.slug}",
            metadata=metadata,
            context=context,
        )

    db.commit()
    return result


def delete_secret(
    db: DbSession,
    principal: Principal,
    project_id: uuid.UUID,
    environment_id: uuid.UUID,
    key: str,
    *,
    context: AuditContext | None = None,
) -> None:
    access, environment = _access(
        db,
        principal,
        project_id,
        environment_id,
        roles={ProjectRole.admin, ProjectRole.editor},
    )
    secret = _secret(db, environment.id, _validate_key(key))
    now = utcnow()
    secret.deleted_at = now
    secret.updated_at = now
    _record(
        db,
        principal,
        access,
        environment,
        action="secret.deleted",
        target=f"secret:{secret.key}",
        metadata={},
        context=context,
    )
    db.commit()


def list_versions(
    db: DbSession,
    principal: Principal,
    project_id: uuid.UUID,
    environment_id: uuid.UUID,
    key: str,
) -> list[SecretVersionOut]:
    _access(db, principal, project_id, environment_id)
    secret = _secret(db, environment_id, _validate_key(key))
    rows = db.execute(
        select(SecretVersion, User)
        .outerjoin(User, User.id == SecretVersion.created_by)
        .where(SecretVersion.secret_id == secret.id)
        .order_by(SecretVersion.version.desc())
    ).all()
    return [
        SecretVersionOut(
            version=version.version,
            keyVersion=version.key_version,
            createdAt=int(to_ms(version.created_at) or 0),
            createdBy=str(version.created_by) if version.created_by else None,
            createdByName=created_by.name if created_by else None,
            createdByEmail=created_by.email if created_by else None,
            comment=version.comment,
        )
        for version, created_by in rows
    ]


def rollback_secret(
    db: DbSession,
    principal: Principal,
    project_id: uuid.UUID,
    environment_id: uuid.UUID,
    key: str,
    request: RollbackRequest,
    *,
    context: AuditContext | None = None,
) -> SecretOut:
    access, environment = _access(
        db,
        principal,
        project_id,
        environment_id,
        roles={ProjectRole.admin, ProjectRole.editor},
    )
    secret = _secret(db, environment.id, _validate_key(key))
    target = db.scalar(
        select(SecretVersion).where(
            SecretVersion.secret_id == secret.id,
            SecretVersion.version == request.version,
        )
    )
    if target is None:
        raise NotFoundError("Secret version not found.")

    aad = secret_aad(
        workspace_id=access.workspace.id,
        project_id=access.project.id,
        environment_id=environment.id,
        key=secret.key,
    )
    _, old_dek = _project_key(db, access.project.id, target.key_version)
    try:
        value = decrypt_secret(target.ciphertext, target.nonce, old_dek, aad=aad)
    except DecryptionError as exc:
        raise UnavailableError("The secret version could not be decrypted.") from exc

    active_key, active_dek = _project_key(db, access.project.id)
    try:
        encrypted = encrypt_secret(value, active_dek, aad=aad)
    except ValueError as exc:
        raise UnavailableError("Encryption is not configured.") from exc

    now = utcnow()
    next_version = _next_version(db, secret.id)
    version = SecretVersion(
        id=uuid.uuid4(),
        secret_id=secret.id,
        version=next_version,
        ciphertext=encrypted.ciphertext,
        nonce=encrypted.nonce,
        key_version=active_key.key_version,
        created_by=principal.user.id if principal.user is not None else None,
        created_at=now,
        comment=f"Rollback to version {target.version}"[:500],
    )
    db.add(version)
    secret.current_version_id = version.id
    secret.updated_at = now
    _record(
        db,
        principal,
        access,
        environment,
        action="secret.rolled_back",
        target=f"secret:{secret.key}",
        metadata={"fromVersion": target.version, "toVersion": next_version},
        context=context,
    )
    db.commit()
    return SecretOut(
        key=secret.key,
        version=next_version,
        comment=version.comment,
        createdAt=int(to_ms(secret.created_at) or 0),
        updatedAt=int(to_ms(secret.updated_at) or 0),
    )


def format_env(values: dict[str, str]) -> str:
    lines = [f"{key}={_quote_env(value)}" for key, value in sorted(values.items())]
    return "\n".join(lines) + ("\n" if lines else "")


def _quote_env(value: str) -> str:
    if value == "":
        return '""'
    if not value.startswith("#") and re.fullmatch(r"[A-Za-z0-9_./:@%+,=-]+", value):
        return value
    escaped = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
    )
    return f'"{escaped}"'
