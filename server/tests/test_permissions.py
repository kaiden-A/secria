import pytest

from app.models import ProjectRole, WorkspaceRole
from app.services.errors import ForbiddenError, NotFoundError
from app.services.permissions import (
    require_project_access,
    require_workspace_admin,
    require_workspace_member,
)


def test_workspace_membership_and_admin_checks(
    db, make_user, make_workspace, add_workspace_member
) -> None:
    owner = make_user(db, email="owner@example.com")
    workspace = make_workspace(owner)

    assert require_workspace_member(db, owner, workspace.id).role is WorkspaceRole.owner
    assert require_workspace_admin(db, owner, workspace.id).role is WorkspaceRole.owner

    member = make_user(db, email="member@example.com")
    add_workspace_member(workspace, member, WorkspaceRole.member)
    assert require_workspace_member(db, member, workspace.id).role is WorkspaceRole.member
    with pytest.raises(ForbiddenError):
        require_workspace_admin(db, member, workspace.id)

    outsider = make_user(db, email="outsider@example.com")
    with pytest.raises(NotFoundError):
        require_workspace_member(db, outsider, workspace.id)


def test_workspace_admin_gets_project_admin(
    db, make_user, make_workspace, add_workspace_member, make_project
) -> None:
    owner = make_user(db, email="owner@example.com")
    workspace = make_workspace(owner)
    project, _envs = make_project(workspace)

    access = require_project_access(db, owner, project.id)
    assert access.project_role is ProjectRole.admin
    assert access.allowed_environment_ids is None

    admin = make_user(db, email="admin@example.com")
    add_workspace_member(workspace, admin, WorkspaceRole.admin)
    access = require_project_access(db, admin, project.id, roles={ProjectRole.admin})
    assert access.project_role is ProjectRole.admin


def test_member_without_a_project_grant_gets_404(
    db, make_user, make_workspace, add_workspace_member, make_project
) -> None:
    owner = make_user(db, email="owner@example.com")
    workspace = make_workspace(owner)
    project, _envs = make_project(workspace)
    member = make_user(db, email="member@example.com")
    add_workspace_member(workspace, member, WorkspaceRole.member)

    with pytest.raises(NotFoundError):
        require_project_access(db, member, project.id)

    with pytest.raises(NotFoundError):
        require_project_access(db, member, project.id, roles={ProjectRole.admin})


def test_viewer_cannot_write_but_editor_can(
    db, make_user, make_workspace, add_workspace_member, make_project, add_project_member
) -> None:
    owner = make_user(db, email="owner@example.com")
    workspace = make_workspace(owner)
    project, _envs = make_project(workspace)

    viewer = make_user(db, email="viewer@example.com")
    add_workspace_member(workspace, viewer, WorkspaceRole.member)
    add_project_member(project, viewer, ProjectRole.viewer)
    assert require_project_access(db, viewer, project.id).project_role is ProjectRole.viewer
    with pytest.raises(ForbiddenError):
        require_project_access(
            db,
            viewer,
            project.id,
            roles={ProjectRole.editor, ProjectRole.admin},
        )

    editor = make_user(db, email="editor@example.com")
    add_workspace_member(workspace, editor, WorkspaceRole.member)
    add_project_member(project, editor, ProjectRole.editor)
    access = require_project_access(
        db,
        editor,
        project.id,
        roles={ProjectRole.editor, ProjectRole.admin},
    )
    assert access.project_role is ProjectRole.editor


def test_environment_restrictions(
    db, make_user, make_workspace, add_workspace_member, make_project, add_project_member
) -> None:
    owner = make_user(db, email="owner@example.com")
    workspace = make_workspace(owner)
    project, envs = make_project(workspace)
    member = make_user(db, email="member@example.com")
    add_workspace_member(workspace, member, WorkspaceRole.member)
    add_project_member(
        project,
        member,
        ProjectRole.viewer,
        environment_ids=[envs[0].id],
    )

    access = require_project_access(db, member, project.id, environment_id=envs[0].id)
    assert access.allowed_environment_ids == frozenset({envs[0].id})

    with pytest.raises(NotFoundError):
        require_project_access(db, member, project.id, environment_id=envs[1].id)


def test_cross_workspace_access_is_404(db, make_user, make_workspace, make_project) -> None:
    alice = make_user(db, email="alice@example.com")
    make_workspace(alice, name="Alice", slug="alice")
    bob = make_user(db, email="bob@example.com")
    bob_workspace = make_workspace(bob, name="Bob", slug="bob")
    bob_project, _envs = make_project(bob_workspace)

    with pytest.raises(NotFoundError):
        require_project_access(db, alice, bob_project.id)

    with pytest.raises(NotFoundError):
        require_workspace_member(db, alice, bob_workspace.id)


def test_project_admin_can_manage(
    db, make_user, make_workspace, add_workspace_member, make_project, add_project_member
) -> None:
    owner = make_user(db, email="owner@example.com")
    workspace = make_workspace(owner)
    project, _envs = make_project(workspace)
    project_admin = make_user(db, email="project-admin@example.com")
    add_workspace_member(workspace, project_admin, WorkspaceRole.member)
    add_project_member(project, project_admin, ProjectRole.admin)

    access = require_project_access(
        db,
        project_admin,
        project.id,
        roles={ProjectRole.admin},
    )
    assert access.project_role is ProjectRole.admin
