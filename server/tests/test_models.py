from sqlalchemy import ForeignKeyConstraint, String, Table

from app.database import Base
from app.models import ProjectRole, ServiceTokenAccess, WorkspaceRole
from app.models.audit import AuditLog

EXPECTED_TABLES = {
    "audit_logs",
    "environments",
    "invite_grants",
    "invites",
    "project_keys",
    "project_member_envs",
    "project_members",
    "projects",
    "secret_versions",
    "secrets",
    "service_tokens",
    "sessions",
    "users",
    "workspace_members",
    "workspaces",
}


def _table(name: str) -> Table:
    return Base.metadata.tables[f"public.{name}"]


def test_every_planned_table_is_registered() -> None:
    assert {table.name for table in Base.metadata.tables.values()} == EXPECTED_TABLES


def test_users_columns_and_unique_indexes() -> None:
    users = _table("users")
    email_type = users.c.email.type
    name_type = users.c.name.type
    subject_type = users.c.zitadel_sub.type
    assert isinstance(email_type, String)
    assert isinstance(name_type, String)
    assert isinstance(subject_type, String)
    assert email_type.length == 320
    assert name_type.length == 200
    assert subject_type.length == 200
    assert {index.name for index in users.indexes} == {
        "ix_public_users_email",
        "ix_public_users_zitadel_sub",
    }


def test_projects_unique_constraint() -> None:
    projects = _table("projects")
    names = {constraint.name for constraint in projects.constraints}
    assert "uq_projects_workspace_slug" in names


def test_secrets_columns_and_constraints() -> None:
    secrets = _table("secrets")
    key_type = secrets.c.key.type
    assert isinstance(key_type, String)
    assert key_type.length == 200
    assert {constraint.name for constraint in secrets.constraints} >= {"uq_secrets_environment_key"}
    assert {index.name for index in secrets.indexes} == {
        "ix_public_secrets_environment_id",
        "ix_public_secrets_current_version_id",
    }


def test_audit_metadata_attribute_maps_to_the_planned_column() -> None:
    audit = _table("audit_logs")
    assert "metadata" in audit.c
    assert AuditLog.meta.property.columns[0].name == "metadata"
    assert {index.name for index in audit.indexes} == {
        "ix_public_audit_logs_workspace_id",
        "ix_public_audit_logs_project_id",
        "ix_public_audit_logs_action",
        "ix_public_audit_logs_created_at",
        "ix_audit_logs_workspace_created",
    }


def test_project_member_envs_composite_foreign_key() -> None:
    table = _table("project_member_envs")
    composite = next(
        constraint
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
        and constraint.name == "project_member_envs_project_id_user_id_fkey"
    )
    assert [element.target_fullname for element in composite.elements] == [
        "project_members.project_id",
        "project_members.user_id",
    ]


def test_enum_values_match_the_database_labels() -> None:
    assert [role.value for role in WorkspaceRole] == ["owner", "admin", "member"]
    assert [role.value for role in ProjectRole] == ["admin", "editor", "viewer"]
    assert [access.value for access in ServiceTokenAccess] == ["read", "read_write"]
