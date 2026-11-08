import uuid

from sqlalchemy import select

from app.models import ProjectMember, Workspace, WorkspaceMember, WorkspaceRole


def _create_workspace(client, name: str = "Acme", slug: str | None = None) -> dict:
    payload: dict[str, object] = {"name": name}
    if slug is not None:
        payload["slug"] = slug
    response = client.post("/api/v1/workspaces", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def _workspace_model(db, body: dict) -> Workspace:
    workspace = db.get(Workspace, uuid.UUID(body["id"]))
    assert workspace is not None
    return workspace


def test_create_list_and_get_workspaces(client, sign_in, make_user, db) -> None:
    user = make_user(db)
    sign_in(user)

    created = _create_workspace(client, "Acme")
    assert created["slug"] == "acme"
    assert created["role"] == "owner"
    assert created["memberCount"] == 1
    assert created["projectCount"] == 0

    listing = client.get("/api/v1/workspaces")
    assert listing.status_code == 200
    assert [workspace["id"] for workspace in listing.json()] == [created["id"]]

    detail = client.get(f"/api/v1/workspaces/{created['id']}")
    assert detail.status_code == 200
    assert detail.json()["name"] == "Acme"


def test_workspace_slug_conflict(client, sign_in, make_user) -> None:
    sign_in(make_user)
    _create_workspace(client, "Acme")

    response = client.post("/api/v1/workspaces", json={"name": "Other", "slug": "acme"})
    assert response.status_code == 409


def test_workspace_update_requires_admin(client, sign_in, make_user, add_workspace_member, db) -> None:
    owner = make_user()
    sign_in(owner)
    created = _create_workspace(client)
    workspace = _workspace_model(db, created)
    member = make_user()
    add_workspace_member(workspace, member, WorkspaceRole.member)

    sign_in(member)
    denied = client.patch(f"/api/v1/workspaces/{created['id']}", json={"name": "Nope"})
    assert denied.status_code == 403

    sign_in(owner)
    updated = client.patch(f"/api/v1/workspaces/{created['id']}", json={"name": "Acme Labs"})
    assert updated.status_code == 200
    assert updated.json()["name"] == "Acme Labs"


def test_workspace_members_include_project_grants(
    client, sign_in, make_user, add_workspace_member, db
) -> None:
    owner = make_user()
    sign_in(owner)
    created = _create_workspace(client)
    workspace = _workspace_model(db, created)
    member = make_user()
    add_workspace_member(workspace, member, WorkspaceRole.member)

    project_response = client.post(
        f"/api/v1/workspaces/{created['id']}/projects", json={"name": "API"}
    )
    assert project_response.status_code == 201, project_response.text
    project = project_response.json()
    grant = client.put(
        f"/api/v1/projects/{project['id']}/members/{member.id}",
        json={"role": "editor"},
    )
    assert grant.status_code == 200, grant.text

    listing = client.get(f"/api/v1/workspaces/{created['id']}/members")
    assert listing.status_code == 200
    members = {row["userId"]: row for row in listing.json()}
    assert members[str(owner.id)]["role"] == "owner"
    assert members[str(member.id)]["role"] == "member"
    assert members[str(member.id)]["projectGrants"][0]["projectName"] == "API"
    assert members[str(member.id)]["projectGrants"][0]["role"] == "editor"


def test_last_owner_cannot_be_demoted_or_removed(client, sign_in, make_user) -> None:
    owner = make_user()
    sign_in(owner)
    created = _create_workspace(client)

    demote = client.patch(
        f"/api/v1/workspaces/{created['id']}/members/{owner.id}",
        json={"role": "admin"},
    )
    assert demote.status_code == 409

    remove = client.delete(f"/api/v1/workspaces/{created['id']}/members/{owner.id}")
    assert remove.status_code == 409


def test_owner_can_demote_when_another_owner_exists(
    client, sign_in, make_user, add_workspace_member, db
) -> None:
    owner = make_user()
    sign_in(owner)
    created = _create_workspace(client)
    workspace = _workspace_model(db, created)
    second_owner = make_user()
    add_workspace_member(workspace, second_owner, WorkspaceRole.owner)

    response = client.patch(
        f"/api/v1/workspaces/{created['id']}/members/{owner.id}",
        json={"role": "admin"},
    )
    assert response.status_code == 200
    assert response.json()["role"] == "admin"


def test_admin_cannot_manage_owners(
    client, sign_in, make_user, add_workspace_member, db
) -> None:
    owner = make_user()
    sign_in(owner)
    created = _create_workspace(client)
    workspace = _workspace_model(db, created)
    admin = make_user()
    add_workspace_member(workspace, admin, WorkspaceRole.admin)

    sign_in(admin)
    demote = client.patch(
        f"/api/v1/workspaces/{created['id']}/members/{owner.id}",
        json={"role": "member"},
    )
    assert demote.status_code == 403

    remove = client.delete(f"/api/v1/workspaces/{created['id']}/members/{owner.id}")
    assert remove.status_code == 403

    promote_self = client.patch(
        f"/api/v1/workspaces/{created['id']}/members/{admin.id}",
        json={"role": "owner"},
    )
    assert promote_self.status_code == 403


def test_removing_a_workspace_member_cascades_project_grants(
    client, sign_in, make_user, add_workspace_member, db
) -> None:
    owner = make_user()
    sign_in(owner)
    created = _create_workspace(client)
    workspace = _workspace_model(db, created)
    member = make_user()
    add_workspace_member(workspace, member, WorkspaceRole.member)
    project = client.post(
        f"/api/v1/workspaces/{created['id']}/projects", json={"name": "API"}
    ).json()
    grant = client.put(
        f"/api/v1/projects/{project['id']}/members/{member.id}",
        json={"role": "editor"},
    )
    assert grant.status_code == 200

    removed = client.delete(f"/api/v1/workspaces/{created['id']}/members/{member.id}")
    assert removed.status_code == 204
    assert db.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace.id,
            WorkspaceMember.user_id == member.id,
        )
    ) is None
    assert db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == uuid.UUID(project["id"]),
            ProjectMember.user_id == member.id,
        )
    ) is None

    sign_in(member)
    assert client.get(f"/api/v1/projects/{project['id']}").status_code == 404


def test_workspace_counts(client, sign_in, make_user) -> None:
    sign_in(make_user)
    created = _create_workspace(client)
    project = client.post(
        f"/api/v1/workspaces/{created['id']}/projects", json={"name": "API"}
    )
    assert project.status_code == 201

    listing = client.get("/api/v1/workspaces").json()
    assert listing[0]["memberCount"] == 1
    assert listing[0]["projectCount"] == 1


def test_cross_workspace_access_is_404(client, sign_in, make_user) -> None:
    alice = make_user()
    sign_in(alice)
    alice_workspace = _create_workspace(client, "Alice", "alice")
    alice_project = client.post(
        f"/api/v1/workspaces/{alice_workspace['id']}/projects", json={"name": "Alice API"}
    ).json()

    bob = make_user()
    sign_in(bob)
    bob_workspace = _create_workspace(client, "Bob", "bob")
    bob_project = client.post(
        f"/api/v1/workspaces/{bob_workspace['id']}/projects", json={"name": "Bob API"}
    ).json()

    sign_in(alice)
    assert client.get(f"/api/v1/workspaces/{bob_workspace['id']}").status_code == 404
    assert client.get(f"/api/v1/workspaces/{bob_workspace['id']}/projects").status_code == 404
    assert client.get(f"/api/v1/projects/{bob_project['id']}").status_code == 404
    assert client.patch(
        f"/api/v1/workspaces/{bob_workspace['id']}", json={"name": "Hijacked"}
    ).status_code == 404
    assert client.delete(f"/api/v1/projects/{alice_project['id']}").status_code == 204
