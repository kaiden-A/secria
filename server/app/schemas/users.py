from pydantic import BaseModel, Field


class PublicUser(BaseModel):
    id: str
    name: str
    email: str
    lastLoginAt: int | None = None


class ProfilePatch(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class SessionOut(BaseModel):
    id: str
    kind: str
    createdAt: int
    lastUsedAt: int | None = None
    expiresAt: int
    ip: str | None = None
    userAgent: str | None = None
    current: bool = False
