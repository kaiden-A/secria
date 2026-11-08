"""Baseline schema for Secria.

Revision ID: 1b77f308b88f
Revises:
Create Date: 2026-11-08

This baseline matches the schema that was provisioned in Neon ahead of the
application code. The live database is already stamped with this revision, so
running ``alembic upgrade head`` against it is a no-op. A fresh database gets
the full schema below.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1b77f308b88f"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


workspace_role = postgresql.ENUM(
    "owner", "admin", "member", name="workspace_role", schema="public", create_type=False
)
project_role = postgresql.ENUM(
    "admin", "editor", "viewer", name="project_role", schema="public", create_type=False
)
service_token_access = postgresql.ENUM(
    "read", "read_write", name="service_token_access", schema="public", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()
    workspace_role.create(bind, checkfirst=True)
    project_role.create(bind, checkfirst=True)
    service_token_access.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("zitadel_sub", sa.String(length=200), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="users_pkey"),
        schema="public",
    )
    op.create_index("ix_public_users_email", "users", ["email"], unique=True, schema="public")
    op.create_index(
        "ix_public_users_zitadel_sub", "users", ["zitadel_sub"], unique=True, schema="public"
    )

    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ip", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["public.users.id"],
            name="sessions_user_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="sessions_pkey"),
        schema="public",
    )
    op.create_index("ix_public_sessions_user_id", "sessions", ["user_id"], schema="public")
    op.create_index(
        "ix_public_sessions_token_hash", "sessions", ["token_hash"], unique=True, schema="public"
    )

    op.create_table(
        "workspaces",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["public.users.id"],
            name="workspaces_created_by_fkey",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="workspaces_pkey"),
        schema="public",
    )
    op.create_index("ix_public_workspaces_slug", "workspaces", ["slug"], unique=True, schema="public")

    op.create_table(
        "workspace_members",
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", workspace_role, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["public.workspaces.id"],
            name="workspace_members_workspace_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["public.users.id"],
            name="workspace_members_user_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("workspace_id", "user_id", name="workspace_members_pkey"),
        schema="public",
    )
    op.create_index(
        "ix_public_workspace_members_user_id", "workspace_members", ["user_id"], schema="public"
    )

    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["public.workspaces.id"],
            name="projects_workspace_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="projects_pkey"),
        sa.UniqueConstraint("workspace_id", "slug", name="uq_projects_workspace_slug"),
        schema="public",
    )
    op.create_index("ix_public_projects_workspace_id", "projects", ["workspace_id"], schema="public")

    op.create_table(
        "project_members",
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", project_role, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["public.projects.id"],
            name="project_members_project_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["public.users.id"],
            name="project_members_user_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("project_id", "user_id", name="project_members_pkey"),
        schema="public",
    )
    op.create_index(
        "ix_public_project_members_user_id", "project_members", ["user_id"], schema="public"
    )

    op.create_table(
        "environments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["public.projects.id"],
            name="environments_project_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="environments_pkey"),
        sa.UniqueConstraint("project_id", "slug", name="uq_environments_project_slug"),
        schema="public",
    )
    op.create_index(
        "ix_public_environments_project_id", "environments", ["project_id"], schema="public"
    )

    op.create_table(
        "project_member_envs",
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("environment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["environment_id"],
            ["public.environments.id"],
            name="project_member_envs_environment_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "user_id"],
            ["public.project_members.project_id", "public.project_members.user_id"],
            name="project_member_envs_project_id_user_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "project_id", "user_id", "environment_id", name="project_member_envs_pkey"
        ),
        schema="public",
    )

    op.create_table(
        "project_keys",
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key_version", sa.Integer(), nullable=False),
        sa.Column("encrypted_dek", sa.LargeBinary(), nullable=False),
        sa.Column("kek_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["public.projects.id"],
            name="project_keys_project_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("project_id", "key_version", name="project_keys_pkey"),
        schema="public",
    )

    op.create_table(
        "secrets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("environment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key", sa.String(length=200), nullable=False),
        sa.Column("current_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["environment_id"],
            ["public.environments.id"],
            name="secrets_environment_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="secrets_pkey"),
        sa.UniqueConstraint("environment_id", "key", name="uq_secrets_environment_key"),
        schema="public",
    )
    op.create_index("ix_public_secrets_environment_id", "secrets", ["environment_id"], schema="public")
    op.create_index(
        "ix_public_secrets_current_version_id", "secrets", ["current_version_id"], schema="public"
    )

    op.create_table(
        "secret_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("secret_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("ciphertext", sa.LargeBinary(), nullable=False),
        sa.Column("nonce", sa.LargeBinary(), nullable=False),
        sa.Column("key_version", sa.Integer(), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("comment", sa.String(length=500), nullable=False),
        sa.ForeignKeyConstraint(
            ["secret_id"],
            ["public.secrets.id"],
            name="secret_versions_secret_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["public.users.id"],
            name="secret_versions_created_by_fkey",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="secret_versions_pkey"),
        sa.UniqueConstraint("secret_id", "version", name="uq_secret_versions_number"),
        schema="public",
    )
    op.create_index(
        "ix_public_secret_versions_secret_id", "secret_versions", ["secret_id"], schema="public"
    )

    op.create_table(
        "invites",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("role", workspace_role, nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("invited_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["public.workspaces.id"],
            name="invites_workspace_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["invited_by"],
            ["public.users.id"],
            name="invites_invited_by_fkey",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="invites_pkey"),
        schema="public",
    )
    op.create_index("ix_public_invites_workspace_id", "invites", ["workspace_id"], schema="public")
    op.create_index("ix_public_invites_email", "invites", ["email"], schema="public")
    op.create_index("ix_public_invites_token_hash", "invites", ["token_hash"], unique=True, schema="public")

    op.create_table(
        "invite_grants",
        sa.Column("invite_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", project_role, nullable=False),
        sa.ForeignKeyConstraint(
            ["invite_id"],
            ["public.invites.id"],
            name="invite_grants_invite_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["public.projects.id"],
            name="invite_grants_project_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("invite_id", "project_id", name="invite_grants_pkey"),
        schema="public",
    )

    op.create_table(
        "service_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("environment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("access", service_token_access, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["public.projects.id"],
            name="service_tokens_project_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["environment_id"],
            ["public.environments.id"],
            name="service_tokens_environment_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["public.users.id"],
            name="service_tokens_created_by_fkey",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="service_tokens_pkey"),
        schema="public",
    )
    op.create_index(
        "ix_public_service_tokens_project_id", "service_tokens", ["project_id"], schema="public"
    )
    op.create_index(
        "ix_public_service_tokens_environment_id",
        "service_tokens",
        ["environment_id"],
        schema="public",
    )
    op.create_index(
        "ix_public_service_tokens_token_hash",
        "service_tokens",
        ["token_hash"],
        unique=True,
        schema="public",
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("environment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_type", sa.String(length=24), nullable=False),
        sa.Column("actor_id", sa.String(length=64), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("target", sa.String(length=320), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("ip", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["public.workspaces.id"],
            name="audit_logs_workspace_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["public.projects.id"],
            name="audit_logs_project_id_fkey",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["environment_id"],
            ["public.environments.id"],
            name="audit_logs_environment_id_fkey",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="audit_logs_pkey"),
        schema="public",
    )
    op.create_index(
        "ix_public_audit_logs_workspace_id", "audit_logs", ["workspace_id"], schema="public"
    )
    op.create_index("ix_public_audit_logs_project_id", "audit_logs", ["project_id"], schema="public")
    op.create_index("ix_public_audit_logs_action", "audit_logs", ["action"], schema="public")
    op.create_index("ix_public_audit_logs_created_at", "audit_logs", ["created_at"], schema="public")
    op.create_index(
        "ix_audit_logs_workspace_created",
        "audit_logs",
        ["workspace_id", "created_at"],
        schema="public",
    )


def downgrade() -> None:
    op.drop_table("audit_logs", schema="public")
    op.drop_table("service_tokens", schema="public")
    op.drop_table("invite_grants", schema="public")
    op.drop_table("invites", schema="public")
    op.drop_table("secret_versions", schema="public")
    op.drop_table("secrets", schema="public")
    op.drop_table("project_keys", schema="public")
    op.drop_table("project_member_envs", schema="public")
    op.drop_table("environments", schema="public")
    op.drop_table("project_members", schema="public")
    op.drop_table("projects", schema="public")
    op.drop_table("workspace_members", schema="public")
    op.drop_table("workspaces", schema="public")
    op.drop_table("sessions", schema="public")
    op.drop_table("users", schema="public")

    bind = op.get_bind()
    service_token_access.drop(bind, checkfirst=True)
    project_role.drop(bind, checkfirst=True)
    workspace_role.drop(bind, checkfirst=True)
