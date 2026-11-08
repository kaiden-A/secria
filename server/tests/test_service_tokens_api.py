import time

from sqlalchemy import select

from app.models import AuditLog, ProjectRole, ServiceToken, WorkspaceRole
from app.services import security

RAW_PREFIX = "secria_st_"


def _tokens_path(project, environment) -> str:
    return (
        f"/api/v1/projects/{project.id}"
        f"/environments/{environment.id}/service-tokens"
    )


def _secrets_path(project, environment) -> str:
    return f"/api/v1/projects/{project.id}/environments/{environment.id}/secrets"


def _create(client, project, environment, **body):
    return client.post(
        _tokens_path(project, environment),
        json={"name": "ci", "access": "read", **body},
    )


def _bearer(raw: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {raw}"}


def test_create_list_and_revoke_token(
    client, sign_in, make_user, make_workspace, make_project, db
) -> None:
    owner = make_user(db)
    workspace = make_workspace(owner)
    project, envs = make_project(workspace)
    sign_in(owner)

    created = _create(client, project, envs[0], name="github-actions")
    assert created.status_code == 201, created.text
    assert created.headers["cache-control"] == "no-store"
    body = created.json()
    assert body["token"].startswith(RAW_PREFIX)
    assert body["name"] == "github-actions"
    assert body["access"] == "read"
    assert body["projectId"] == str(project.id)
    assert body["environmentId"] == str(envs[0].id)
    assert body["revokedAt"] is None

    row = db.scalar(select(ServiceToken).where(ServiceToken.id == body["id"]))
    assert row is not None
    assert row.token_hash == security.hash_token(body["token"])
    assert body["token"] not in row.token_hash

    listing = client.get(_tokens_path(project, envs[0]))
    assert listing.status_code == 200
    assert len(listing.json()) == 1
    assert listing.json()[0]["name"] == "github-actions"
    assert "token" not in listing.json()[0]
    assert "tokenHash" not in listing.json()[0]

    revoked = client.delete(f"{_tokens_path(project, envs[0])}/{body['id']}")
    assert revoked.status_code == 204
    db.expire_all()
    row = db.get(ServiceToken, body["id"])
    assert row is not None and row.revoked_at is not None

    # Revoking twice is a no-op, not an error.
    assert client.delete(f"{_tokens_path(project, envs[0])}/{body['id']}").status_code == 204
    listing = client.get(_tokens_path(project, envs[0])).json()
    assert listing[0]["revokedAt"] is not None

    actions = {
        log.action
        for log in db.scalars(
            select(AuditLog).where(AuditLog.workspace_id == workspace.id)
        ).all()
    }
    assert {"service_token.created", "service_token.revoked"} <= actions


def test_read_token_cannot_write_but_read_write_can(
    client, sign_in, make_user, make_workspace, make_project, db
) -> None:
    owner = make_user(db)
    workspace = make_workspace(owner)
    project, envs = make_project(workspace)
    sign_in(owner)

    read_token = _create(client, project, envs[0], access="read").json()["token"]
    write_token = _create(client, project, envs[0], access="read_write").json()["token"]

    # Read token: list, reveal, and download work.
    assert client.get(_secrets_path(project, envs[0]), headers=_bearer(read_token)).status_code == 200
    created = client.put(
        _secrets_path(project, envs[0]),
        json={"mode": "merge", "secrets": [{"key": "API_KEY", "value": "one"}]},
        headers=_bearer(write_token),
    )
    assert created.status_code == 200, created.text
    assert created.json()["added"] == 1

    reveal = client.get(
        f"{_secrets_path(project, envs[0])}/API_KEY", headers=_bearer(read_token)
    )
    assert reveal.status_code == 200
    assert reveal.json()["value"] == "one"
    assert reveal.headers["cache-control"] == "no-store"

    denied = client.put(
        _secrets_path(project, envs[0]),
        json={"mode": "merge", "secrets": [{"key": "OTHER", "value": "two"}]},
        headers=_bearer(read_token),
    )
    assert denied.status_code == 403
    assert "read-only" in denied.json()["error"].lower()

    assert client.delete(
        f"{_secrets_path(project, envs[0])}/API_KEY", headers=_bearer(read_token)
    ).status_code == 403

    # Diff is a read, but the endpoint is not gated on write.
    assert client.post(
        f"{_secrets_path(project, envs[0])}/diff",
        json={"secrets": [{"key": "API_KEY", "valueSha256": "0" * 64}]},
        headers=_bearer(read_token),
    ).status_code == 200


def test_scope_is_limited_to_one_project_environment(
    client, sign_in, make_user, make_workspace, make_project, db
) -> None:
    owner = make_user(db)
    workspace = make_workspace(owner)
    project, envs = make_project(workspace)
    other_project, other_envs = make_project(workspace, name="Other")
    sign_in(owner)
    raw = _create(client, project, envs[0]).json()["token"]

    same = client.get(_secrets_path(project, envs[0]), headers=_bearer(raw))
    assert same.status_code == 200

    # Another environment in the same project is outside the token.
    assert client.get(_secrets_path(project, envs[1]), headers=_bearer(raw)).status_code == 404
    # Another project is outside the token.
    assert (
        client.get(_secrets_path(other_project, other_envs[0]), headers=_bearer(raw)).status_code
        == 404
    )


def test_current_scope_endpoint(client, sign_in, make_user, make_workspace, make_project, db) -> None:
    owner = make_user(db)
    workspace = make_workspace(owner)
    project, envs = make_project(workspace)
    sign_in(owner)
    raw = _create(client, project, envs[1], name="deployer").json()["token"]

    scope = client.get("/api/v1/service-tokens/current", headers=_bearer(raw))
    assert scope.status_code == 200, scope.text
    body = scope.json()
    assert body["name"] == "deployer"
    assert body["workspaceId"] == str(workspace.id)
    assert body["workspaceSlug"] == workspace.slug
    assert body["projectId"] == str(project.id)
    assert body["projectSlug"] == project.slug
    assert body["environmentId"] == str(envs[1].id)
    assert body["environmentSlug"] == "staging"

    # A user session cannot use the service-token scope endpoint.
    assert client.get("/api/v1/service-tokens/current").status_code == 401


def test_service_token_cannot_use_user_endpoints(
    client, sign_in, make_user, make_workspace, make_project, db
) -> None:
    owner = make_user(db)
    workspace = make_workspace(owner)
    project, envs = make_project(workspace)
    sign_in(owner)
    raw = _create(client, project, envs[0]).json()["token"]

    assert client.get("/api/v1/me", headers=_bearer(raw)).status_code == 401
    assert client.get("/api/v1/workspaces", headers=_bearer(raw)).status_code == 401
    assert client.get(
        "/api/v1/workspaces", headers={"Authorization": "Bearer secria_st_bogus"}
    ).status_code == 401

    # Service tokens cannot mint or revoke other service tokens.
    assert client.get(_tokens_path(project, envs[0]), headers=_bearer(raw)).status_code == 401
    assert (
        client.post(
            _tokens_path(project, envs[0]),
            json={"name": "nested", "access": "read"},
            headers=_bearer(raw),
        ).status_code
        == 401
    )


def test_revoked_and_expired_tokens_are_rejected(
    client, sign_in, make_user, make_workspace, make_project, db
) -> None:
    owner = make_user(db)
    workspace = make_workspace(owner)
    project, envs = make_project(workspace)
    sign_in(owner)

    revoked = _create(client, project, envs[0], name="revoked").json()
    client.delete(f"{_tokens_path(project, envs[0])}/{revoked['id']}")
    response = client.get(_secrets_path(project, envs[0]), headers=_bearer(revoked["token"]))
    assert response.status_code == 401
    assert "revoked" in response.json()["error"].lower()

    expired = _create(
        client,
        project,
        envs[0],
        name="expired",
        expiresAt=int((time.time() + 60) * 1000),
    ).json()
    db.expire_all()
    row = db.get(ServiceToken, expired["id"])
    assert row is not None
    row.expires_at = row.created_at.replace(year=2000)
    db.commit()

    response = client.get(_secrets_path(project, envs[0]), headers=_bearer(expired["token"]))
    assert response.status_code == 401
    assert "expired" in response.json()["error"].lower()


def test_only_project_admins_manage_tokens(
    client,
    sign_in,
    make_user,
    make_workspace,
    make_project,
    add_project_member,
    add_workspace_member,
    db,
) -> None:
    owner = make_user(db, email="owner@example.com")
    workspace = make_workspace(owner)
    project, envs = make_project(workspace)

    editor = make_user(db, email="editor@example.com")
    add_workspace_member(workspace, editor, WorkspaceRole.member)
    add_project_member(project, editor, ProjectRole.editor)
    outsider = make_user(db, email="outsider@example.com")

    sign_in(owner)
    token = _create(client, project, envs[0]).json()

    sign_in(editor)
    assert _create(client, project, envs[0], name="editor").status_code == 403
    assert client.get(_tokens_path(project, envs[0])).status_code == 403
    assert (
        client.delete(f"{_tokens_path(project, envs[0])}/{token['id']}").status_code == 403
    )

    sign_in(outsider)
    assert _create(client, project, envs[0], name="outsider").status_code == 404
    assert client.get(_tokens_path(project, envs[0])).status_code == 404

    # A workspace admin gets implicit project admin.
    admin = make_user(db, email="admin@example.com")
    add_workspace_member(workspace, admin, WorkspaceRole.admin)
    sign_in(admin)
    assert _create(client, project, envs[0], name="admin").status_code == 201


def test_expiry_must_be_in_the_future(
    client, sign_in, make_user, make_workspace, make_project, db
) -> None:
    owner = make_user(db)
    workspace = make_workspace(owner)
    project, envs = make_project(workspace)
    sign_in(owner)

    response = _create(
        client, project, envs[0], expiresAt=int((time.time() - 60) * 1000)
    )
    assert response.status_code == 422
    assert "future" in response.json()["error"].lower()


def test_token_cannot_target_an_environment_of_another_project(
    client, sign_in, make_user, make_workspace, make_project, db
) -> None:
    owner = make_user(db)
    workspace = make_workspace(owner)
    project, envs = make_project(workspace)
    other_project, other_envs = make_project(workspace, name="Other")
    sign_in(owner)

    # Cross-project environment id under the first project must 404.
    response = client.post(
        f"/api/v1/projects/{project.id}/environments/{other_envs[0].id}/service-tokens",
        json={"name": "bad", "access": "read"},
    )
    assert response.status_code == 404

    token = _create(client, project, envs[0]).json()
    # Revoking through the wrong environment must 404.
    response = client.delete(
        f"/api/v1/projects/{project.id}/environments/{other_envs[0].id}"
        f"/service-tokens/{token['id']}"
    )
    assert response.status_code == 404
