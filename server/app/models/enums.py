from enum import StrEnum


class WorkspaceRole(StrEnum):
    owner = "owner"
    admin = "admin"
    member = "member"


class ProjectRole(StrEnum):
    admin = "admin"
    editor = "editor"
    viewer = "viewer"


class ServiceTokenAccess(StrEnum):
    read = "read"
    read_write = "read_write"


def enum_values(enum_class: type[StrEnum]) -> list[str]:
    """SQLAlchemy values_callable: store the lowercase value, not the name."""
    return [member.value for member in enum_class]
