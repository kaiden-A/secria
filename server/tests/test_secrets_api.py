import hashlib

from sqlalchemy import select

from app.models import (
    AuditLog,
    ProjectRole,
    Secret,
    SecretVersion,
    WorkspaceRole,
)
from app.services import secret_services


def _path(project, environment) -> str:
    return f"/api/v1/projects/{project.id}/environments/{environment.id}/secrets"


def _upsert(client, project, environment, secrets, mode: str = "merge"):
    return client.put(_path(project, environment), json={"secrets": secrets, "mode": mode})


def _list(client, project, environment):
    return client.get(_path(project, environment))


def _reveal(client, project, environment, key: str):
    return client.get(f"{_path(project, environment)}/{key}")


def _download(client, project, environment, format: str = "env"):
    return client.get(f"{_path(project, environment)}/download", params={"format": format})


def _diff(client, project, environment, secrets):
    return client.post(f"{_path(project, environment)}/diff", json={"secrets": secrets})


def _copy_preview(client, project, environment, source):
    return client.post(
        f"{_path(project, environment)}/copy/preview",
        json={"sourceEnvironmentId": str(source.id)},
    )


def _copy(client, project, environment, source, mode: str = "merge"):
    return client.post(
        f"{_path(project, environment)}/copy",
        json={"sourceEnvironmentId": str(source.id), "mode": mode},
    )


def _secret(db, environment, key: str) -> Secret:
    row = db.scalar(
        select(Secret).where(Secret.environment_id == environment.id, Secret.key == key)
    )
    assert row is not None
    return row


def _versions(db, environment, key: str) -> list[SecretVersion]:
    secret = _secret(db, environment, key)
    return list(
        db.scalars(
            select(SecretVersion)
            .where(SecretVersion.secret_id == secret.id)
            .order_by(SecretVersion.version)
        ).all()
    )


def test_bulk_upsert_creates_encrypted_versions_and_masked_list(
    client, sign_in, make_user, make_workspace, make_project, db
) -> None:
    owner = make_user(db)
    workspace = make_workspace(owner)
    project, envs = make_project(workspace)
    sign_in(owner)

    response = _upsert(
        client,
        project,
        envs[0],
        [
            {"key": "DATABASE_URL", "value": "postgres://user:pass@db/app"},
            {"key": "API_KEY", "value": "super-secret"},
        ],
    )
    assert response.status_code == 200, response.text
    assert response.json() == {"added": 2, "updated": 0, "removed": 0, "unchanged": 0}

    listing = _list(client, project, envs[0])
    assert listing.status_code == 200
    assert listing.headers["cache-control"] == "no-store"
    rows = listing.json()
    assert [row["key"] for row in rows] == ["API_KEY", "DATABASE_URL"]
    assert all("value" not in row for row in rows)
    assert all(row["version"] == 1 for row in rows)

    database = _secret(db, envs[0], "DATABASE_URL")
    assert database.current_version_id is not None
    versions = _versions(db, envs[0], "DATABASE_URL")
    assert len(versions) == 1
    assert b"postgres" not in versions[0].ciphertext


def test_unchanged_values_do_not_create_versions_and_changes_do(
    client, sign_in, make_user, make_workspace, make_project, db
) -> None:
    owner = make_user(db)
    workspace = make_workspace(owner)
    project, envs = make_project(workspace)
    sign_in(owner)

    assert _upsert(client, project, envs[0], [{"key": "TOKEN", "value": "v1"}]).json()[
        "added"
    ] == 1
    unchanged = _upsert(client, project, envs[0], [{"key": "TOKEN", "value": "v1"}])
    assert unchanged.json()["unchanged"] == 1
    assert len(_versions(db, envs[0], "TOKEN")) == 1

    updated = _upsert(client, project, envs[0], [{"key": "TOKEN", "value": "v2"}])
    assert updated.json()["updated"] == 1
    versions = _versions(db, envs[0], "TOKEN")
    assert [version.version for version in versions] == [1, 2]
    assert _reveal(client, project, envs[0], "TOKEN").json()["value"] == "v2"


def test_reveal_is_audited_without_logging_the_value(
    client, sign_in, make_user, make_workspace, make_project, db
) -> None:
    owner = make_user(db)
    workspace = make_workspace(owner)
    project, envs = make_project(workspace)
    sign_in(owner)
    _upsert(client, project, envs[0], [{"key": "DATABASE_URL", "value": "postgres://secret"}])

    response = _reveal(client, project, envs[0], "DATABASE_URL")
    assert response.status_code == 200
    assert response.json()["value"] == "postgres://secret"
    assert response.headers["cache-control"] == "no-store"

    audit = db.scalar(select(AuditLog).where(AuditLog.action == "secret.revealed"))
    assert audit is not None
    assert audit.target == "secret:DATABASE_URL"
    assert audit.meta == {"version": 1}
    assert "postgres://secret" not in str(audit.meta)


def test_download_env_and_json(client, sign_in, make_user, make_workspace, make_project, db) -> None:
    owner = make_user(db)
    workspace = make_workspace(owner)
    project, envs = make_project(workspace)
    sign_in(owner)
    values = {
        "PLAIN": "abc",
        "SPACED": "hello world",
        "MULTI": "line1\nline2",
        "REF": "${HOME}",
        "QUOTED": 'say "hi"',
        "EMPTY": "",
    }
    _upsert(
        client,
        project,
        envs[0],
        [{"key": key, "value": value} for key, value in values.items()],
    )

    env_response = _download(client, project, envs[0])
    assert env_response.status_code == 200
    assert env_response.headers["cache-control"] == "no-store"
    assert "attachment" in env_response.headers["content-disposition"]
    text = env_response.text
    assert "PLAIN=abc" in text
    assert 'SPACED="hello world"' in text
    assert 'MULTI="line1\\nline2"' in text
    assert 'REF="${HOME}"' in text
    assert 'QUOTED="say \\"hi\\""' in text
    assert 'EMPTY=""' in text

    json_response = _download(client, project, envs[0], "json")
    assert json_response.status_code == 200
    assert json_response.json() == values

    audit = db.scalar(select(AuditLog).where(AuditLog.action == "secret.downloaded"))
    assert audit is not None
    assert audit.meta["count"] == 6


def test_diff_reports_added_changed_removed_unchanged(
    client, sign_in, make_user, make_workspace, make_project, db
) -> None:
    owner = make_user(db)
    workspace = make_workspace(owner)
    project, envs = make_project(workspace)
    sign_in(owner)
    _upsert(
        client,
        project,
        envs[0],
        [
            {"key": "SAME", "value": "one"},
            {"key": "CHANGED", "value": "two"},
            {"key": "REMOVED", "value": "three"},
        ],
    )
    digest = lambda value: hashlib.sha256(value.encode()).hexdigest()  # noqa: E731

    response = _diff(
        client,
        project,
        envs[0],
        [
            {"key": "SAME", "valueSha256": digest("one")},
            {"key": "CHANGED", "valueSha256": digest("changed")},
            {"key": "ADDED", "valueSha256": digest("new")},
        ],
    )
    assert response.status_code == 200, response.text
    assert response.json() == {
        "added": ["ADDED"],
        "changed": ["CHANGED"],
        "removed": ["REMOVED"],
        "unchanged": ["SAME"],
    }
    assert response.headers["cache-control"] == "no-store"


def test_replace_mode_soft_deletes_and_restore_continues_versions(
    client, sign_in, make_user, make_workspace, make_project, db
) -> None:
    owner = make_user(db)
    workspace = make_workspace(owner)
    project, envs = make_project(workspace)
    sign_in(owner)
    _upsert(
        client,
        project,
        envs[0],
        [{"key": "KEEP", "value": "a"}, {"key": "DROP", "value": "b"}],
    )

    replaced = _upsert(
        client,
        project,
        envs[0],
        [{"key": "KEEP", "value": "a"}],
        mode="replace",
    )
    assert replaced.json() == {"added": 0, "updated": 0, "removed": 1, "unchanged": 1}
    assert [row["key"] for row in _list(client, project, envs[0]).json()] == ["KEEP"]
    dropped = _secret(db, envs[0], "DROP")
    assert dropped.deleted_at is not None

    restored = _upsert(client, project, envs[0], [{"key": "DROP", "value": "new"}])
    assert restored.json()["added"] == 1
    assert [version.version for version in _versions(db, envs[0], "DROP")] == [1, 2]
    assert _reveal(client, project, envs[0], "DROP").json()["value"] == "new"


def test_secret_key_and_size_validation(
    client, sign_in, make_user, make_workspace, make_project, db
) -> None:
    owner = make_user(db)
    workspace = make_workspace(owner)
    project, envs = make_project(workspace)
    sign_in(owner)

    assert _upsert(client, project, envs[0], [{"key": "lowercase", "value": "x"}]).status_code == 422
    assert _upsert(client, project, envs[0], [{"key": "1BAD", "value": "x"}]).status_code == 422
    assert _upsert(
        client,
        project,
        envs[0],
        [{"key": "A", "value": "x"}, {"key": "A", "value": "y"}],
    ).status_code == 422
    assert _upsert(
        client,
        project,
        envs[0],
        [{"key": "BIG", "value": "x" * (64 * 1024 + 1)}],
    ).status_code == 422
    too_many = [{"key": f"K{index}", "value": "x"} for index in range(1001)]
    assert _upsert(client, project, envs[0], too_many).status_code == 422


def test_viewer_editor_and_outsider_permissions(
    client,
    sign_in,
    make_user,
    make_workspace,
    make_project,
    add_workspace_member,
    add_project_member,
    db,
) -> None:
    owner = make_user(db)
    workspace = make_workspace(owner)
    project, envs = make_project(workspace)
    viewer = make_user(db)
    editor = make_user(db)
    outsider = make_user(db)
    add_workspace_member(workspace, viewer, WorkspaceRole.member)
    add_workspace_member(workspace, editor, WorkspaceRole.member)
    add_project_member(project, viewer, ProjectRole.viewer)
    add_project_member(project, editor, ProjectRole.editor)

    sign_in(viewer)
    assert _list(client, project, envs[0]).status_code == 200
    assert _upsert(client, project, envs[0], [{"key": "A", "value": "x"}]).status_code == 403
    assert _reveal(client, project, envs[0], "A").status_code == 404

    sign_in(editor)
    assert _upsert(client, project, envs[0], [{"key": "A", "value": "x"}]).status_code == 200
    assert _reveal(client, project, envs[0], "A").json()["value"] == "x"

    sign_in(outsider)
    assert _list(client, project, envs[0]).status_code == 404


def test_environment_restrictions_apply_to_secret_routes(
    client,
    sign_in,
    make_user,
    make_workspace,
    make_project,
    add_workspace_member,
    add_project_member,
    db,
) -> None:
    owner = make_user(db)
    workspace = make_workspace(owner)
    project, envs = make_project(workspace)
    member = make_user(db)
    add_workspace_member(workspace, member, WorkspaceRole.member)
    add_project_member(
        project,
        member,
        ProjectRole.editor,
        environment_ids=[envs[0].id],
    )

    sign_in(owner)
    _upsert(client, project, envs[0], [{"key": "DEV_ONLY", "value": "dev"}])
    _upsert(client, project, envs[2], [{"key": "PROD_ONLY", "value": "prod"}])

    sign_in(member)
    assert _reveal(client, project, envs[0], "DEV_ONLY").status_code == 200
    assert _list(client, project, envs[2]).status_code == 404
    assert _upsert(client, project, envs[2], [{"key": "NOPE", "value": "x"}]).status_code == 404


def test_cross_workspace_secret_access_is_404(
    client, sign_in, make_user, make_workspace, make_project, db
) -> None:
    alice = make_user(db)
    alice_workspace = make_workspace(alice)
    alice_project, alice_envs = make_project(alice_workspace)
    bob = make_user(db)
    bob_workspace = make_workspace(bob)
    bob_project, bob_envs = make_project(bob_workspace)
    sign_in(alice)
    _upsert(client, alice_project, alice_envs[0], [{"key": "ALICE", "value": "a"}])

    assert _list(client, bob_project, bob_envs[0]).status_code == 404
    assert _reveal(client, bob_project, bob_envs[0], "ALICE").status_code == 404
    assert _upsert(
        client, bob_project, bob_envs[0], [{"key": "NOPE", "value": "x"}]
    ).status_code == 404


def test_delete_soft_deletes_and_restore_continues_versions(
    client, sign_in, make_user, make_workspace, make_project, db
) -> None:
    owner = make_user(db)
    workspace = make_workspace(owner)
    project, envs = make_project(workspace)
    sign_in(owner)
    _upsert(client, project, envs[0], [{"key": "DELETE_ME", "value": "v1"}])

    response = client.delete(f"{_path(project, envs[0])}/DELETE_ME")
    assert response.status_code == 204
    assert _list(client, project, envs[0]).json() == []
    assert _reveal(client, project, envs[0], "DELETE_ME").status_code == 404
    assert _secret(db, envs[0], "DELETE_ME").deleted_at is not None

    restored = _upsert(client, project, envs[0], [{"key": "DELETE_ME", "value": "v2"}])
    assert restored.json()["added"] == 1
    assert [version.version for version in _versions(db, envs[0], "DELETE_ME")] == [1, 2]


def test_rollback_creates_a_new_version_and_is_audited(
    client, sign_in, make_user, make_workspace, make_project, db
) -> None:
    owner = make_user(db)
    workspace = make_workspace(owner)
    project, envs = make_project(workspace)
    sign_in(owner)
    _upsert(client, project, envs[0], [{"key": "ROLL", "value": "v1"}])
    _upsert(client, project, envs[0], [{"key": "ROLL", "value": "v2"}])

    response = client.post(
        f"{_path(project, envs[0])}/ROLL/rollback", json={"version": 1}
    )
    assert response.status_code == 200, response.text
    assert response.json()["version"] == 3
    assert _reveal(client, project, envs[0], "ROLL").json()["value"] == "v1"

    versions = client.get(f"{_path(project, envs[0])}/ROLL/versions")
    assert versions.status_code == 200
    assert [version["version"] for version in versions.json()] == [3, 2, 1]
    assert versions.json()[0]["comment"] == "Rollback to version 1"

    audit = db.scalar(select(AuditLog).where(AuditLog.action == "secret.rolled_back"))
    assert audit is not None
    assert audit.meta == {"fromVersion": 1, "toVersion": 3}

    assert client.post(
        f"{_path(project, envs[0])}/ROLL/rollback", json={"version": 99}
    ).status_code == 404


def test_audit_log_filters_cursor_and_no_value_leakage(
    client,
    sign_in,
    make_user,
    make_workspace,
    make_project,
    add_workspace_member,
    db,
) -> None:
    owner = make_user(db)
    workspace = make_workspace(owner)
    project, envs = make_project(workspace)
    sign_in(owner)
    _upsert(client, project, envs[0], [{"key": "SECRET_ONE", "value": "do-not-log-me"}])
    _reveal(client, project, envs[0], "SECRET_ONE")
    _download(client, project, envs[0], "json")

    audit_path = f"/api/v1/workspaces/{workspace.id}/audit-logs"
    response = client.get(audit_path)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    page = response.json()
    assert page["items"]
    assert "do-not-log-me" not in response.text
    actions = {item["action"] for item in page["items"]}
    assert "secret.created" in actions
    assert "secret.revealed" in actions
    assert "secret.downloaded" in actions

    filtered = client.get(audit_path, params={"action": "secret.revealed"})
    assert filtered.status_code == 200
    assert [item["action"] for item in filtered.json()["items"]] == ["secret.revealed"]

    by_actor = client.get(audit_path, params={"actor": owner.email})
    assert by_actor.status_code == 200
    assert by_actor.json()["items"]

    by_project = client.get(audit_path, params={"project": str(project.id)})
    assert by_project.status_code == 200
    assert by_project.json()["items"]

    first = client.get(audit_path, params={"limit": 1})
    assert first.status_code == 200
    assert len(first.json()["items"]) == 1
    assert first.json()["nextCursor"]
    second = client.get(audit_path, params={"limit": 1, "cursor": first.json()["nextCursor"]})
    assert second.status_code == 200
    assert second.json()["items"][0]["id"] != first.json()["items"][0]["id"]

    member = make_user(db)
    add_workspace_member(workspace, member, WorkspaceRole.member)
    sign_in(member)
    assert client.get(audit_path).status_code == 403


def test_copy_preview_and_merge_between_environments(
    client, sign_in, make_user, make_workspace, make_project, db
) -> None:
    owner = make_user(db)
    workspace = make_workspace(owner)
    project, envs = make_project(workspace)
    dev, _staging, prod = envs
    sign_in(owner)
    _upsert(
        client,
        project,
        dev,
        [
            {"key": "SHARED", "value": "same"},
            {"key": "CHANGED", "value": "dev-value"},
            {"key": "DEV_ONLY", "value": "dev-only"},
        ],
    )
    _upsert(
        client,
        project,
        prod,
        [
            {"key": "SHARED", "value": "same"},
            {"key": "CHANGED", "value": "prod-value"},
            {"key": "PROD_ONLY", "value": "prod-only"},
        ],
    )

    preview = _copy_preview(client, project, prod, dev)
    assert preview.status_code == 200, preview.text
    assert preview.headers["cache-control"] == "no-store"
    assert preview.json() == {
        "added": ["DEV_ONLY"],
        "changed": ["CHANGED"],
        "removed": ["PROD_ONLY"],
        "unchanged": ["SHARED"],
    }

    copied = _copy(client, project, prod, dev)
    assert copied.status_code == 200, copied.text
    assert copied.json() == {"added": 1, "updated": 1, "removed": 0, "unchanged": 1}
    assert [row["key"] for row in _list(client, project, prod).json()] == [
        "CHANGED",
        "DEV_ONLY",
        "PROD_ONLY",
        "SHARED",
    ]
    assert _reveal(client, project, prod, "CHANGED").json()["value"] == "dev-value"
    assert [version.version for version in _versions(db, prod, "CHANGED")] == [1, 2]
    assert [version.version for version in _versions(db, prod, "SHARED")] == [1]

    dev_ciphertext = _versions(db, dev, "CHANGED")[-1].ciphertext
    prod_ciphertext = _versions(db, prod, "CHANGED")[-1].ciphertext
    assert dev_ciphertext != prod_ciphertext

    preview_audit = db.scalar(select(AuditLog).where(AuditLog.action == "secret.diffed"))
    assert preview_audit is not None
    assert preview_audit.meta["sourceEnvironment"] == "dev"

    audit = db.scalar(select(AuditLog).where(AuditLog.action == "secret.copied"))
    assert audit is not None
    assert audit.meta["sourceEnvironment"] == "dev"
    assert audit.meta["added"] == 1
    assert audit.meta["updated"] == 1
    assert "dev-value" not in str(audit.meta)


def test_copy_replace_mirrors_source_and_soft_deletes_target_only_keys(
    client, sign_in, make_user, make_workspace, make_project, db
) -> None:
    owner = make_user(db)
    workspace = make_workspace(owner)
    project, envs = make_project(workspace)
    dev, _staging, prod = envs
    sign_in(owner)
    _upsert(client, project, dev, [{"key": "KEEP", "value": "from-dev"}])
    _upsert(
        client,
        project,
        prod,
        [{"key": "KEEP", "value": "old"}, {"key": "EXTRA", "value": "prod-only"}],
    )

    copied = _copy(client, project, prod, dev, mode="replace")
    assert copied.status_code == 200, copied.text
    assert copied.json() == {"added": 0, "updated": 1, "removed": 1, "unchanged": 0}
    assert [row["key"] for row in _list(client, project, prod).json()] == ["KEEP"]
    assert _reveal(client, project, prod, "KEEP").json()["value"] == "from-dev"
    assert _secret(db, prod, "EXTRA").deleted_at is not None


def test_copy_rejects_same_environment_viewers_and_restricted_targets(
    client,
    sign_in,
    make_user,
    make_workspace,
    make_project,
    add_workspace_member,
    add_project_member,
    db,
) -> None:
    owner = make_user(db)
    workspace = make_workspace(owner)
    project, envs = make_project(workspace)
    dev, _staging, prod = envs
    sign_in(owner)
    _upsert(client, project, dev, [{"key": "DEV", "value": "dev"}])

    assert _copy(client, project, dev, dev).status_code == 422
    assert _copy_preview(client, project, dev, dev).status_code == 422

    _other_project, other_envs = make_project(workspace, name="Other")
    assert _copy(client, project, prod, other_envs[0]).status_code == 404

    viewer = make_user(db)
    add_workspace_member(workspace, viewer, WorkspaceRole.member)
    add_project_member(project, viewer, ProjectRole.viewer)
    sign_in(viewer)
    assert _copy_preview(client, project, prod, dev).status_code == 200
    assert _copy(client, project, prod, dev).status_code == 403

    restricted = make_user(db)
    add_workspace_member(workspace, restricted, WorkspaceRole.member)
    add_project_member(
        project,
        restricted,
        ProjectRole.editor,
        environment_ids=[dev.id],
    )
    sign_in(restricted)
    assert _copy(client, project, prod, dev).status_code == 404
    assert _copy_preview(client, project, prod, dev).status_code == 404


def test_format_env_quotes_only_what_needs_quoting() -> None:
    text = secret_services.format_env(
        {
            "A": "abc",
            "B": "hello world",
            "C": "line1\nline2",
            "D": 'say "hi"',
            "E": "${HOME}",
            "F": "",
            "G": "back\\slash",
        }
    )
    assert "A=abc" in text
    assert 'B="hello world"' in text
    assert 'C="line1\\nline2"' in text
    assert 'D="say \\"hi\\""' in text
    assert 'E="${HOME}"' in text
    assert 'F=""' in text
    assert 'G="back\\\\slash"' in text
