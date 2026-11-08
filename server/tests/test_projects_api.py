import uuid

from sqlalchemy import func, select

from app.models import (
    Environment,
    ProjectKey,
    ProjectMember,
    ProjectMemberEnv,
    Workspace,
    WorkspaceRole,
)
from app.services.encryption import get_master_key


def _create_workspace(client, name: str = "Acme") -> dict:
    response = client.post("/api/v1/workspaces", json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()


def _create_project(client, workspace_id: str, name: str = "API") -> dict:
    response = client.post(
        f"/api/v1/workspaces/{workspace_id}/projects", json={"name": name}
    )
    assert response.status_code == 201, response.text
    return response.json()


def _workspace_model(db, body: dict) -> Workspace:
    workspace = db.get(Workspace, uuid.UUID(body["id"]))
    assert workspace is not None
    return workspace


def _grant(client, project_id: str, user_id: uuid.UUID, role: str, environment_ids=None):
    payload: dict[str, object] = {"role": role}
    if environment_ids is not None:
        payload["environmentIds"] = [str(environment_id) for environment_id in environment_ids]
    return client.put(f"/api/v1/projects/{project_id}/members/{user_id}", json=payload)


def test_create_project_creates_defaults_and_a_wrapped_key(
    client, sign_in, make_user, db
) -> None:
    sign_in(make_user(db))
    workspace = _create_workspace(client)

    response = client.post(
        f"/api/v1/workspaces/{workspace['id']}/projects",
        json={"name": "API", "description": "Core API"},
    )
    assert response.status_code == 201, response.text
    project = response.json()
    assert project["role"] == "admin"
    assert project["description"] == "Core API"
    assert [environment["slug"] for environment in project["environments"]] == [
        "dev",
        "staging",
        "prod",
    ]
    assert [environment["position"] for environment in project["environments"]] == [0, 1, 2]
    assert project["environmentCount"] == 3

    project_id = uuid.UUID(project["id"])
    key = db.scalar(select(ProjectKey).where(ProjectKey.project_id == project_id))
    assert key is not None
    master = get_master_key()
    dek = master.unwrap_dek(
        key.encrypted_dek,
        project_id=project_id,
        key_version=key.key_version,
        kek_version=key.kek_version,
    )
    assert len(dek) == 32


def test_project_list_for_owner_and_member(
    client, sign_in, make_user, add_workspace_member, db
) -> None:
    owner = make_user(db)
    sign_in(owner)
    workspace = _create_workspace(client)
    project = _create_project(client, workspace["id"])
    workspace_model = _workspace_model(db, workspace)
    member = make_user(db)
    add_workspace_member(workspace_model, member, WorkspaceRole.member)

    sign_in(member)
    assert client.get(f"/api/v1/workspaces/{workspace['id']}/projects").json() == []
    assert client.get(f"/api/v1/projects/{project['id']}").status_code == 404

    sign_in(owner)
    grant = _grant(client, project["id"], member.id, "viewer")
    assert grant.status_code == 200, grant.text

    sign_in(member)
    listing = client.get(f"/api/v1/workspaces/{workspace['id']}/projects")
    assert listing.status_code == 200
    assert [row["id"] for row in listing.json()] == [project["id"]]
    assert listing.json()[0]["role"] == "viewer"
    detail = client.get(f"/api/v1/projects/{project['id']}")
    assert detail.status_code == 200
    assert detail.json()["role"] == "viewer"
    assert len(detail.json()["environments"]) == 3


def test_environment_restrictions_filter_detail_and_block_writes(
    client, sign_in, make_user, add_workspace_member, db
) -> None:
    owner = make_user(db)
    sign_in(owner)
    workspace = _create_workspace(client)
    project = _create_project(client, workspace["id"])
    workspace_model = _workspace_model(db, workspace)
    member = make_user(db)
    add_workspace_member(workspace_model, member, WorkspaceRole.member)
    dev = project["environments"][0]

    grant = _grant(client, project["id"], member.id, "viewer", [dev["id"]])
    assert grant.status_code == 200, grant.text
    assert grant.json()["environmentIds"] == [dev["id"]]

    sign_in(member)
    detail = client.get(f"/api/v1/projects/{project['id']}").json()
    assert [environment["slug"] for environment in detail["environments"]] == ["dev"]
    assert detail["environmentCount"] == 1
    listing = client.get(f"/api/v1/workspaces/{workspace['id']}/projects").json()
    assert listing[0]["environmentCount"] == 1
    environments = client.get(f"/api/v1/projects/{project['id']}/environments").json()
    assert [environment["slug"] for environment in environments] == ["dev"]

    assert client.patch(
        f"/api/v1/projects/{project['id']}", json={"name": "Nope"}
    ).status_code == 403
    assert client.post(
        f"/api/v1/projects/{project['id']}/environments", json={"name": "QA"}
    ).status_code == 403


def test_project_members_include_workspace_admins(
    client, sign_in, make_user, add_workspace_member, db
) -> None:
    owner = make_user(db)
    sign_in(owner)
    workspace = _create_workspace(client)
    project = _create_project(client, workspace["id"])
    workspace_model = _workspace_model(db, workspace)
    admin = make_user(db)
    add_workspace_member(workspace_model, admin, WorkspaceRole.admin)
    viewer = make_user(db)
    add_workspace_member(workspace_model, viewer, WorkspaceRole.member)
    assert _grant(client, project["id"], viewer.id, "viewer").status_code == 200

    response = client.get(f"/api/v1/projects/{project['id']}/members")
    assert response.status_code == 200
    members = {row["userId"]: row for row in response.json()}
    assert members[str(owner.id)]["role"] == "admin"
    assert members[str(admin.id)]["role"] == "admin"
    assert members[str(viewer.id)]["role"] == "viewer"
    assert members[str(viewer.id)]["environmentIds"] is None


def test_invalid_environment_and_non_member_grants_are_rejected(
    client, sign_in, make_user, add_workspace_member, db
) -> None:
    owner = make_user(db)
    sign_in(owner)
    workspace = _create_workspace(client)
    project = _create_project(client, workspace["id"])
    other_project = _create_project(client, workspace["id"], "Worker")
    workspace_model = _workspace_model(db, workspace)
    member = make_user(db)
    add_workspace_member(workspace_model, member, WorkspaceRole.member)

    invalid = _grant(
        client,
        project["id"],
        member.id,
        "viewer",
        [other_project["environments"][0]["id"]],
    )
    assert invalid.status_code == 422

    outsider = make_user(db)
    missing = _grant(client, project["id"], outsider.id, "viewer")
    assert missing.status_code == 404


def test_project_slug_conflict_and_patch(client, sign_in, make_user, db) -> None:
    user = make_user(db)
    sign_in(user)
    workspace = _create_workspace(client)
    first = _create_project(client, workspace["id"], "API")
    second = _create_project(client, workspace["id"], "Worker")

    duplicate = client.post(
        f"/api/v1/workspaces/{workspace['id']}/projects",
        json={"name": "Duplicate", "slug": first["slug"]},
    )
    assert duplicate.status_code == 409

    conflict = client.patch(
        f"/api/v1/projects/{second['id']}", json={"slug": first["slug"]}
    )
    assert conflict.status_code == 409

    renamed = client.patch(f"/api/v1/projects/{second['id']}", json={"slug": "worker-2"})
    assert renamed.status_code == 200
    assert renamed.json()["slug"] == "worker-2"


def test_environment_create_and_duplicate(client, sign_in, make_user, db) -> None:
    user = make_user(db)
    sign_in(user)
    workspace = _create_workspace(client)
    project = _create_project(client, workspace["id"])

    created = client.post(
        f"/api/v1/projects/{project['id']}/environments", json={"name": "QA"}
    )
    assert created.status_code == 201
    assert created.json()["slug"] == "qa"
    assert created.json()["position"] == 3

    duplicate = client.post(
        f"/api/v1/projects/{project['id']}/environments", json={"name": "QA"}
    )
    assert duplicate.status_code == 409

    environments = client.get(f"/api/v1/projects/{project['id']}/environments").json()
    assert len(environments) == 4


def test_archive_project_hides_it_from_lists_but_keeps_it_readable(
    client, sign_in, make_user, db
) -> None:
    user = make_user(db)
    sign_in(user)
    workspace = _create_workspace(client)
    project = _create_project(client, workspace["id"])

    archived = client.patch(f"/api/v1/projects/{project['id']}", json={"archived": True})
    assert archived.status_code == 200
    assert archived.json()["archivedAt"] is not None
    assert client.get(f"/api/v1/workspaces/{workspace['id']}/projects").json() == []
    assert client.get(f"/api/v1/projects/{project['id']}").status_code == 200

    restored = client.patch(f"/api/v1/projects/{project['id']}", json={"archived": False})
    assert restored.status_code == 200
    assert restored.json()["archivedAt"] is None
    assert len(client.get(f"/api/v1/workspaces/{workspace['id']}/projects").json()) == 1


def test_delete_project_requires_admin_and_cascades(
    client, sign_in, make_user, add_workspace_member, db
) -> None:
    owner = make_user(db)
    sign_in(owner)
    workspace = _create_workspace(client)
    project = _create_project(client, workspace["id"])
    workspace_model = _workspace_model(db, workspace)
    editor = make_user(db)
    add_workspace_member(workspace_model, editor, WorkspaceRole.member)
    assert _grant(client, project["id"], editor.id, "editor").status_code == 200

    sign_in(editor)
    assert client.delete(f"/api/v1/projects/{project['id']}").status_code == 403

    sign_in(owner)
    assert client.delete(f"/api/v1/projects/{project['id']}").status_code == 204
    assert client.get(f"/api/v1/projects/{project['id']}").status_code == 404
    project_id = uuid.UUID(project["id"])
    assert db.scalar(
        select(func.count()).select_from(Environment).where(Environment.project_id == project_id)
    ) == 0
    assert db.scalar(
        select(func.count()).select_from(ProjectKey).where(ProjectKey.project_id == project_id)
    ) == 0
    assert db.scalar(
        select(func.count())
        .select_from(ProjectMember)
        .where(ProjectMember.project_id == project_id)
    ) == 0
    assert db.scalar(
        select(func.count())
        .select_from(ProjectMemberEnv)
        .where(ProjectMemberEnv.project_id == project_id)
    ) == 0


def test_project_creation_requires_workspace_admin(
    client, sign_in, make_user, add_workspace_member, db
) -> None:
    owner = make_user(db)
    sign_in(owner)
    workspace = _create_workspace(client)
    workspace_model = _workspace_model(db, workspace)
    member = make_user(db)
    add_workspace_member(workspace_model, member, WorkspaceRole.member)

    sign_in(member)
    response = client.post(
        f"/api/v1/workspaces/{workspace['id']}/projects", json={"name": "Nope"}
    )
    assert response.status_code == 403


def test_project_member_grant_can_be_updated_and_removed(
    client, sign_in, make_user, add_workspace_member, db
) -> None:
    owner = make_user(db)
    sign_in(owner)
    workspace = _create_workspace(client)
    project = _create_project(client, workspace["id"])
    workspace_model = _workspace_model(db, workspace)
    member = make_user(db)
    add_workspace_member(workspace_model, member, WorkspaceRole.member)

    first = _grant(client, project["id"], member.id, "editor")
    assert first.status_code == 200
    assert first.json()["role"] == "editor"

    updated = _grant(client, project["id"], member.id, "viewer")
    assert updated.status_code == 200
    assert updated.json()["role"] == "viewer"

    removed = client.delete(f"/api/v1/projects/{project['id']}/members/{member.id}")
    assert removed.status_code == 204

    sign_in(member)
    assert client.get(f"/api/v1/projects/{project['id']}").status_code == 404
