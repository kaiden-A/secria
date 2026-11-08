import uuid
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.config import get_settings
from app.models import (
    AuditLog,
    Invite,
    ProjectMember,
    ProjectRole,
    WorkspaceMember,
    WorkspaceRole,
    utcnow,
)
from app.services import email_services, security

settings = get_settings()


@pytest.fixture
def sent_emails(monkeypatch, _emails_off):
    calls: list[dict] = []

    def fake_deliver(*, to: str, subject: str, html: str, text: str) -> str:
        calls.append({"to": to, "subject": subject, "html": html, "text": text})
        return f"fake-{len(calls)}"

    monkeypatch.setattr(email_services, "_deliver", fake_deliver)
    monkeypatch.setattr(settings, "resend_api_key", "test-key")
    monkeypatch.setattr(settings, "email_override_to", "")
    return calls


def _create_invite(client, workspace, email: str, *, role: str = "member", grants=None):
    return client.post(
        f"/api/v1/workspaces/{workspace.id}/invites",
        json={"email": email, "role": role, "grants": grants or []},
    )


def _token(url: str) -> str:
    return url.rstrip("/").rsplit("/", 1)[-1]


def _invite_row(db, body: dict) -> Invite:
    invite = db.get(Invite, uuid.UUID(body["id"]))
    assert invite is not None
    return invite


def _grant(project, role: str) -> dict:
    return {"projectId": str(project.id), "role": role}


def test_create_invite_sends_email_stores_hash_and_lists(
    client, sign_in, make_user, make_workspace, make_project, db, sent_emails
) -> None:
    owner = make_user(db, name="Ada", email="owner@example.com")
    workspace = make_workspace(owner)
    project, _envs = make_project(workspace)
    sign_in(owner)

    response = _create_invite(
        client,
        workspace,
        "new@example.com",
        grants=[_grant(project, "editor")],
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["email"] == "new@example.com"
    assert body["role"] == "member"
    assert body["status"] == "pending"
    assert body["grants"][0]["projectName"] == "API"
    assert body["grants"][0]["role"] == "editor"
    assert body["inviteUrl"].startswith("http://localhost:3000/invite/")
    assert body["emailSent"] is True

    token = _token(body["inviteUrl"])
    invite = _invite_row(db, body)
    assert invite.token_hash == security.hash_token(token)
    assert token not in invite.token_hash

    assert len(sent_emails) == 1
    assert sent_emails[0]["to"] == "new@example.com"
    assert workspace.name in sent_emails[0]["subject"]
    assert body["inviteUrl"] in sent_emails[0]["html"]
    assert body["inviteUrl"] in sent_emails[0]["text"]

    listing = client.get(f"/api/v1/workspaces/{workspace.id}/invites")
    assert listing.status_code == 200
    assert len(listing.json()) == 1
    assert listing.json()[0]["status"] == "pending"
    assert "inviteUrl" not in listing.json()[0]


def test_preview_and_accept_matching_email(
    client, sign_in, make_user, make_workspace, make_project, db, sent_emails
) -> None:
    owner = make_user(db, email="owner@example.com")
    workspace = make_workspace(owner)
    project, _envs = make_project(workspace)
    sign_in(owner)
    body = _create_invite(
        client, workspace, "new@example.com", grants=[_grant(project, "editor")]
    ).json()
    token = _token(body["inviteUrl"])

    invitee = make_user(db, name="New Person", email="new@example.com")
    sign_in(invitee)
    preview = client.get(f"/api/v1/invites/{token}")
    assert preview.status_code == 200
    assert preview.json()["workspaceName"] == workspace.name
    assert preview.json()["workspaceSlug"] == workspace.slug
    assert preview.json()["role"] == "member"
    assert preview.json()["grants"][0]["role"] == "editor"

    accepted = client.post(f"/api/v1/invites/{token}/accept")
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["workspaceId"] == str(workspace.id)
    assert accepted.json()["workspaceSlug"] == workspace.slug

    membership = db.get(WorkspaceMember, (workspace.id, invitee.id))
    assert membership is not None
    assert membership.role == WorkspaceRole.member
    grant = db.get(ProjectMember, (project.id, invitee.id))
    assert grant is not None
    assert grant.role == ProjectRole.editor
    assert _invite_row(db, body).accepted_at is not None

    audit = db.scalar(select(AuditLog).where(AuditLog.action == "invite.accepted"))
    assert audit is not None
    assert audit.actor_id == str(invitee.id)

    again = client.post(f"/api/v1/invites/{token}/accept")
    assert again.status_code == 422

    sign_in(owner)
    listing = client.get(f"/api/v1/workspaces/{workspace.id}/invites")
    assert listing.json()[0]["status"] == "accepted"


def test_wrong_email_cannot_preview_or_accept(
    client, sign_in, make_user, make_workspace, db, sent_emails
) -> None:
    owner = make_user(db, email="owner@example.com")
    workspace = make_workspace(owner)
    sign_in(owner)
    body = _create_invite(client, workspace, "new@example.com").json()
    token = _token(body["inviteUrl"])

    other = make_user(db, email="other@example.com")
    sign_in(other)
    assert client.get(f"/api/v1/invites/{token}").status_code == 403
    assert client.post(f"/api/v1/invites/{token}/accept").status_code == 403
    assert db.get(WorkspaceMember, (workspace.id, other.id)) is None


def test_expired_and_revoked_invites(
    client, sign_in, make_user, make_workspace, db, sent_emails
) -> None:
    owner = make_user(db, email="owner@example.com")
    workspace = make_workspace(owner)
    sign_in(owner)

    first = _create_invite(client, workspace, "expired@example.com").json()
    invite = _invite_row(db, first)
    invite.expires_at = utcnow() - timedelta(seconds=1)
    db.commit()

    invitee = make_user(db, email="expired@example.com")
    sign_in(invitee)
    token = _token(first["inviteUrl"])
    assert client.get(f"/api/v1/invites/{token}").status_code == 422
    assert client.post(f"/api/v1/invites/{token}/accept").status_code == 422

    sign_in(owner)
    listing = client.get(f"/api/v1/workspaces/{workspace.id}/invites").json()
    assert listing[0]["status"] == "expired"

    second = _create_invite(client, workspace, "revoked@example.com").json()
    revoked = client.delete(f"/api/v1/workspaces/{workspace.id}/invites/{second['id']}")
    assert revoked.status_code == 204
    assert _invite_row(db, second).revoked_at is not None
    assert client.delete(
        f"/api/v1/workspaces/{workspace.id}/invites/{second['id']}"
    ).status_code == 204

    listing = client.get(f"/api/v1/workspaces/{workspace.id}/invites").json()
    assert {item["status"] for item in listing} == {"expired", "revoked"}
    assert client.get(f"/api/v1/invites/{_token(second['inviteUrl'])}").status_code == 422


def test_resend_rotates_token_and_extends_expiry(
    client, sign_in, make_user, make_workspace, db, sent_emails
) -> None:
    owner = make_user(db, email="owner@example.com")
    workspace = make_workspace(owner)
    sign_in(owner)
    first = _create_invite(client, workspace, "new@example.com").json()
    old_token = _token(first["inviteUrl"])
    invite = _invite_row(db, first)
    invite.expires_at = utcnow() - timedelta(seconds=1)
    db.commit()

    response = client.post(f"/api/v1/workspaces/{workspace.id}/invites/{first['id']}/resend")
    assert response.status_code == 200, response.text
    new_token = _token(response.json()["inviteUrl"])
    assert new_token != old_token
    assert response.json()["emailSent"] is True
    assert len(sent_emails) == 2
    assert _invite_row(db, first).token_hash == security.hash_token(new_token)
    assert _invite_row(db, first).expires_at > utcnow()

    invitee = make_user(db, email="new@example.com")
    sign_in(invitee)
    assert client.get(f"/api/v1/invites/{old_token}").status_code == 404
    assert client.get(f"/api/v1/invites/{new_token}").status_code == 200


def test_update_invite_role_and_grants(
    client, sign_in, make_user, make_workspace, make_project, db, sent_emails
) -> None:
    owner = make_user(db, email="owner@example.com")
    workspace = make_workspace(owner)
    project, _envs = make_project(workspace)
    sign_in(owner)
    body = _create_invite(
        client, workspace, "new@example.com", grants=[_grant(project, "viewer")]
    ).json()

    updated = client.patch(
        f"/api/v1/workspaces/{workspace.id}/invites/{body['id']}",
        json={"role": "admin", "grants": [_grant(project, "editor")]},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["role"] == "admin"
    assert updated.json()["grants"][0]["role"] == "editor"

    invitee = make_user(db, email="new@example.com")
    sign_in(invitee)
    preview = client.get(f"/api/v1/invites/{_token(body['inviteUrl'])}").json()
    assert preview["role"] == "admin"
    assert preview["grants"][0]["role"] == "editor"
    assert client.post(f"/api/v1/invites/{_token(body['inviteUrl'])}/accept").status_code == 200
    assert db.get(WorkspaceMember, (workspace.id, invitee.id)).role == WorkspaceRole.admin
    assert db.get(ProjectMember, (project.id, invitee.id)).role == ProjectRole.editor


def test_admin_cannot_grant_owner_but_owner_can(
    client, sign_in, make_user, make_workspace, add_workspace_member, db, sent_emails
) -> None:
    owner = make_user(db, email="owner@example.com")
    workspace = make_workspace(owner)
    admin = make_user(db, email="admin@example.com")
    add_workspace_member(workspace, admin, WorkspaceRole.admin)

    sign_in(owner)
    existing = _create_invite(client, workspace, "pending@example.com").json()
    sign_in(admin)
    assert _create_invite(client, workspace, "owner2@example.com", role="owner").status_code == 403
    assert (
        client.patch(
            f"/api/v1/workspaces/{workspace.id}/invites/{existing['id']}",
            json={"role": "owner"},
        ).status_code
        == 403
    )

    sign_in(owner)
    assert _create_invite(client, workspace, "owner2@example.com", role="owner").status_code == 201


def test_invite_permissions_and_cross_workspace(
    client, sign_in, make_user, make_workspace, add_workspace_member, db, sent_emails
) -> None:
    owner = make_user(db, email="owner@example.com")
    workspace = make_workspace(owner)
    member = make_user(db, email="member@example.com")
    add_workspace_member(workspace, member, WorkspaceRole.member)

    sign_in(owner)
    invite = _create_invite(client, workspace, "pending@example.com").json()
    sign_in(member)
    assert client.get(f"/api/v1/workspaces/{workspace.id}/invites").status_code == 403
    assert _create_invite(client, workspace, "nope@example.com").status_code == 403
    assert client.patch(
        f"/api/v1/workspaces/{workspace.id}/invites/{invite['id']}",
        json={"role": "member"},
    ).status_code == 403
    assert client.post(
        f"/api/v1/workspaces/{workspace.id}/invites/{invite['id']}/resend"
    ).status_code == 403
    assert client.delete(
        f"/api/v1/workspaces/{workspace.id}/invites/{invite['id']}"
    ).status_code == 403

    outsider = make_user(db, email="outsider@example.com")
    sign_in(outsider)
    assert client.get(f"/api/v1/workspaces/{workspace.id}/invites").status_code == 404

    other_owner = make_user(db, email="other-owner@example.com")
    other_workspace = make_workspace(other_owner)
    sign_in(other_owner)
    assert client.get(f"/api/v1/workspaces/{workspace.id}/invites").status_code == 404
    assert _create_invite(client, other_workspace, "other@example.com").status_code == 201


def test_duplicate_pending_and_existing_member(
    client, sign_in, make_user, make_workspace, add_workspace_member, db, sent_emails
) -> None:
    owner = make_user(db, email="owner@example.com")
    workspace = make_workspace(owner)
    sign_in(owner)

    first = _create_invite(client, workspace, "dup@example.com")
    assert first.status_code == 201
    assert _create_invite(client, workspace, "dup@example.com").status_code == 409

    invite = _invite_row(db, first.json())
    invite.expires_at = utcnow() - timedelta(seconds=1)
    db.commit()
    assert _create_invite(client, workspace, "dup@example.com").status_code == 201

    member = make_user(db, email="member@example.com")
    add_workspace_member(workspace, member, WorkspaceRole.member)
    assert _create_invite(client, workspace, "member@example.com").status_code == 409


def test_invite_grant_validation(
    client, sign_in, make_user, make_workspace, make_project, db, sent_emails
) -> None:
    owner = make_user(db, email="owner@example.com")
    workspace = make_workspace(owner)
    project, _envs = make_project(workspace)
    sign_in(owner)

    other_owner = make_user(db, email="other-owner@example.com")
    other_workspace = make_workspace(other_owner)
    other_project, _other_envs = make_project(other_workspace)

    assert _create_invite(
        client,
        workspace,
        "cross@example.com",
        grants=[_grant(other_project, "viewer")],
    ).status_code == 404
    assert _create_invite(
        client,
        workspace,
        "dupe@example.com",
        grants=[_grant(project, "viewer"), _grant(project, "editor")],
    ).status_code == 422

    project.archived_at = utcnow()
    db.commit()
    assert _create_invite(
        client,
        workspace,
        "archived@example.com",
        grants=[_grant(project, "viewer")],
    ).status_code == 404


def test_invite_without_email_key_still_returns_link(
    client, sign_in, make_user, make_workspace, db
) -> None:
    owner = make_user(db, email="owner@example.com")
    workspace = make_workspace(owner)
    sign_in(owner)

    response = _create_invite(client, workspace, "offline@example.com")
    assert response.status_code == 201
    body = response.json()
    assert body["emailSent"] is False
    assert body["inviteUrl"].startswith("http://localhost:3000/invite/")


def test_invite_audit_actions_and_no_token_leakage(
    client, sign_in, make_user, make_workspace, make_project, db, sent_emails
) -> None:
    owner = make_user(db, email="owner@example.com")
    workspace = make_workspace(owner)
    project, _envs = make_project(workspace)
    sign_in(owner)
    first = _create_invite(
        client, workspace, "new@example.com", grants=[_grant(project, "viewer")]
    ).json()
    token = _token(first["inviteUrl"])
    client.patch(
        f"/api/v1/workspaces/{workspace.id}/invites/{first['id']}",
        json={"role": "admin"},
    )
    resend = client.post(
        f"/api/v1/workspaces/{workspace.id}/invites/{first['id']}/resend"
    )
    new_token = _token(resend.json()["inviteUrl"])

    second = _create_invite(client, workspace, "revoked@example.com").json()
    client.delete(f"/api/v1/workspaces/{workspace.id}/invites/{second['id']}")

    listing = client.get(f"/api/v1/workspaces/{workspace.id}/audit-logs")
    assert listing.status_code == 200
    actions = {item["action"] for item in listing.json()["items"]}
    assert {"invite.created", "invite.updated", "invite.resent", "invite.revoked"} <= actions
    assert token not in listing.text
    assert new_token not in listing.text
    assert _token(second["inviteUrl"]) not in listing.text


def test_invite_preview_requires_auth(client) -> None:
    assert client.get("/api/v1/invites/whatever").status_code == 401
    assert client.post("/api/v1/invites/whatever/accept").status_code == 401
