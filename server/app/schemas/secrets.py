from typing import Literal

from pydantic import BaseModel, Field


class SecretOut(BaseModel):
    key: str
    version: int | None = None
    comment: str = ""
    createdAt: int
    updatedAt: int


class SecretValueOut(BaseModel):
    key: str
    value: str
    version: int


class SecretVersionOut(BaseModel):
    version: int
    keyVersion: int
    createdAt: int
    createdBy: str | None = None
    createdByName: str | None = None
    createdByEmail: str | None = None
    comment: str = ""


class BulkSecretInput(BaseModel):
    key: str = Field(min_length=1, max_length=200)
    value: str
    comment: str = Field(default="", max_length=500)


class BulkUpsertRequest(BaseModel):
    secrets: list[BulkSecretInput] = Field(default_factory=list, max_length=1000)
    mode: Literal["merge", "replace"] = "merge"


class BulkUpsertResult(BaseModel):
    added: int
    updated: int
    removed: int
    unchanged: int


class DiffSecretInput(BaseModel):
    key: str = Field(min_length=1, max_length=200)
    valueSha256: str | None = Field(default=None, max_length=64)


class DiffRequest(BaseModel):
    secrets: list[DiffSecretInput] = Field(default_factory=list, max_length=1000)


class DiffResult(BaseModel):
    added: list[str]
    changed: list[str]
    removed: list[str]
    unchanged: list[str]


class RollbackRequest(BaseModel):
    version: int = Field(ge=1)
