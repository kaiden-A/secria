import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy.orm import Session as DbSession

from ..database import get_db
from ..dependencies import Principal, require_principal
from ..rate_limit import COPY_LIMIT, DOWNLOAD_LIMIT, REVEAL_LIMIT, limiter
from ..schemas.secrets import (
    BulkUpsertRequest,
    BulkUpsertResult,
    CopySecretsRequest,
    DiffRequest,
    DiffResult,
    RollbackRequest,
    SecretOut,
    SecretValueOut,
    SecretVersionOut,
)
from ..services import secret_services
from ..services.audit_services import AuditContext

router = APIRouter(prefix="/api/v1", tags=["secrets"])


def _context(request: Request) -> AuditContext:
    return AuditContext(
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.get(
    "/projects/{project_id}/environments/{environment_id}/secrets",
    response_model=list[SecretOut],
)
def list_secrets(
    project_id: uuid.UUID,
    environment_id: uuid.UUID,
    principal: Principal = Depends(require_principal),
    db: DbSession = Depends(get_db),
) -> list[SecretOut]:
    return secret_services.list_secrets(db, principal, project_id, environment_id)


@router.get("/projects/{project_id}/environments/{environment_id}/secrets/download")
@limiter.limit(DOWNLOAD_LIMIT)
def download_secrets(
    project_id: uuid.UUID,
    environment_id: uuid.UUID,
    request: Request,
    format: Literal["env", "json"] = Query(default="env"),
    principal: Principal = Depends(require_principal),
    db: DbSession = Depends(get_db),
) -> Response:
    values = secret_services.download_secrets(
        db,
        principal,
        project_id,
        environment_id,
        format=format,
        context=_context(request),
    )
    if format == "env":
        return PlainTextResponse(
            secret_services.format_env(values),
            headers={"Content-Disposition": 'attachment; filename="secrets.env"'},
        )
    return JSONResponse(values)


@router.put(
    "/projects/{project_id}/environments/{environment_id}/secrets",
    response_model=BulkUpsertResult,
)
def bulk_upsert(
    project_id: uuid.UUID,
    environment_id: uuid.UUID,
    request_body: BulkUpsertRequest,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: DbSession = Depends(get_db),
) -> BulkUpsertResult:
    return secret_services.bulk_upsert(
        db,
        principal,
        project_id,
        environment_id,
        request_body,
        context=_context(request),
    )


@router.post(
    "/projects/{project_id}/environments/{environment_id}/secrets/diff",
    response_model=DiffResult,
)
def diff_secrets(
    project_id: uuid.UUID,
    environment_id: uuid.UUID,
    request_body: DiffRequest,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: DbSession = Depends(get_db),
) -> DiffResult:
    return secret_services.diff_secrets(
        db,
        principal,
        project_id,
        environment_id,
        request_body,
        context=_context(request),
    )


@router.post(
    "/projects/{project_id}/environments/{environment_id}/secrets/copy/preview",
    response_model=DiffResult,
)
@limiter.limit(COPY_LIMIT)
def preview_copy_secrets(
    project_id: uuid.UUID,
    environment_id: uuid.UUID,
    request_body: CopySecretsRequest,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: DbSession = Depends(get_db),
) -> DiffResult:
    return secret_services.preview_copy_secrets(
        db,
        principal,
        project_id,
        environment_id,
        request_body,
        context=_context(request),
    )


@router.post(
    "/projects/{project_id}/environments/{environment_id}/secrets/copy",
    response_model=BulkUpsertResult,
)
@limiter.limit(COPY_LIMIT)
def copy_secrets(
    project_id: uuid.UUID,
    environment_id: uuid.UUID,
    request_body: CopySecretsRequest,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: DbSession = Depends(get_db),
) -> BulkUpsertResult:
    return secret_services.copy_secrets(
        db,
        principal,
        project_id,
        environment_id,
        request_body,
        context=_context(request),
    )


@router.get(
    "/projects/{project_id}/environments/{environment_id}/secrets/{key}",
    response_model=SecretValueOut,
)
@limiter.limit(REVEAL_LIMIT)
def reveal_secret(
    project_id: uuid.UUID,
    environment_id: uuid.UUID,
    key: str,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: DbSession = Depends(get_db),
) -> SecretValueOut:
    return secret_services.reveal_secret(
        db,
        principal,
        project_id,
        environment_id,
        key,
        context=_context(request),
    )


@router.delete(
    "/projects/{project_id}/environments/{environment_id}/secrets/{key}",
    status_code=204,
)
def delete_secret(
    project_id: uuid.UUID,
    environment_id: uuid.UUID,
    key: str,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: DbSession = Depends(get_db),
) -> None:
    secret_services.delete_secret(
        db,
        principal,
        project_id,
        environment_id,
        key,
        context=_context(request),
    )


@router.get(
    "/projects/{project_id}/environments/{environment_id}/secrets/{key}/versions",
    response_model=list[SecretVersionOut],
)
def list_versions(
    project_id: uuid.UUID,
    environment_id: uuid.UUID,
    key: str,
    principal: Principal = Depends(require_principal),
    db: DbSession = Depends(get_db),
) -> list[SecretVersionOut]:
    return secret_services.list_versions(db, principal, project_id, environment_id, key)


@router.post(
    "/projects/{project_id}/environments/{environment_id}/secrets/{key}/rollback",
    response_model=SecretOut,
)
def rollback_secret(
    project_id: uuid.UUID,
    environment_id: uuid.UUID,
    key: str,
    request_body: RollbackRequest,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: DbSession = Depends(get_db),
) -> SecretOut:
    return secret_services.rollback_secret(
        db,
        principal,
        project_id,
        environment_id,
        key,
        request_body,
        context=_context(request),
    )
