from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.config import get_settings
from app.models import Session as SessionRow
from app.models import User
from app.services import security

settings = get_settings()


def _start_login(client: TestClient, fake_idp) -> str:
    response = client.get("/api/auth/login?next=/w/acme")
    assert response.status_code == 302
    return fake_idp.authorize_requests[-1]["state"]


def test_login_redirects_to_idp_and_sets_oauth_cookie(idp_client, fake_idp, client) -> None:
    response = idp_client.get(
        "/api/auth/login?next=/w/acme&login_hint=ada@example.com&prompt=login"
    )
    assert response.status_code == 302
    assert response.headers["location"].startswith("https://idp.test/authorize")
    assert client.cookies.get(security.OAUTH_COOKIE)
    request = fake_idp.authorize_requests[-1]
    assert request["login_hint"] == "ada@example.com"
    assert request["prompt"] == "login"
    assert request["redirect_uri"] == settings.zitadel_redirect_uri
    assert request["code_challenge"]


def test_signup_requests_the_create_prompt(idp_client, fake_idp) -> None:
    response = idp_client.post("/api/auth/signup")
    assert response.status_code == 302
    assert fake_idp.authorize_requests[-1]["prompt"] == "create"


def test_callback_creates_user_and_session(idp_client, fake_idp, client, db: DbSession) -> None:
    state = _start_login(idp_client, fake_idp)

    response = idp_client.get(f"/api/auth/callback?code=abc&state={state}")

    assert response.status_code == 302
    assert response.headers["location"] == "/w/acme"
    assert client.cookies.get(settings.session_cookie_name)
    me = idp_client.get("/api/v1/me")
    assert me.status_code == 200
    body = me.json()
    assert body["email"] == "ada@example.com"
    assert body["name"] == "Ada Lovelace"
    assert body["lastLoginAt"] is not None
    assert fake_idp.token_requests[0]["code"] == "abc"
    assert fake_idp.verify_calls[0]["nonce"] == fake_idp.authorize_requests[-1]["nonce"]

    user = db.scalar(select(User))
    assert user is not None
    assert user.zitadel_sub == "sub-ada"
    assert user.last_login_at is not None


def test_callback_rejects_bad_state(idp_client, fake_idp) -> None:
    _start_login(idp_client, fake_idp)
    response = idp_client.get("/api/auth/callback?code=abc&state=wrong")
    assert response.status_code == 401
    assert response.json()["error"] == "Could not finish signing in. Please try again."


def test_callback_redirects_when_the_idp_reports_an_error(idp_client, fake_idp) -> None:
    _start_login(idp_client, fake_idp)
    response = idp_client.get("/api/auth/callback?error=access_denied")
    assert response.status_code == 302
    assert response.headers["location"].startswith("http://localhost:3000/login?error=")


def test_callback_rejects_unverified_email(idp_client, fake_idp, db: DbSession) -> None:
    fake_idp.claims["email_verified"] = False
    state = _start_login(idp_client, fake_idp)

    response = idp_client.get(f"/api/auth/callback?code=abc&state={state}")

    assert response.status_code == 403
    assert db.scalar(select(User)) is None


def test_callback_adopts_an_invited_placeholder(idp_client, fake_idp, db: DbSession) -> None:
    placeholder = User(name="Ada", email="ada@example.com", zitadel_sub=None)
    db.add(placeholder)
    db.commit()

    state = _start_login(idp_client, fake_idp)
    response = idp_client.get(f"/api/auth/callback?code=abc&state={state}")

    assert response.status_code == 302
    db.refresh(placeholder)
    assert placeholder.zitadel_sub == "sub-ada"
    assert len(db.scalars(select(User)).all()) == 1


def test_callback_rejects_an_email_owned_by_another_subject(
    idp_client, fake_idp, db: DbSession
) -> None:
    db.add(User(name="Someone", email="ada@example.com", zitadel_sub="other-sub"))
    db.commit()
    state = _start_login(idp_client, fake_idp)

    response = idp_client.get(f"/api/auth/callback?code=abc&state={state}")

    assert response.status_code == 409
    assert len(db.scalars(select(User)).all()) == 1


def test_session_expiry_is_enforced_and_deleted(
    client, sign_in, make_user, db: DbSession
) -> None:
    user = make_user(db)
    token = sign_in(user)
    row = db.scalar(select(SessionRow).where(SessionRow.token_hash == security.hash_token(token)))
    assert row is not None
    row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db.commit()

    response = client.get("/api/v1/me")

    assert response.status_code == 401
    assert db.scalar(select(SessionRow)) is None


def test_logout_revokes_the_session(idp_client, fake_idp, client, sign_in, make_user, db) -> None:
    user = make_user(db)
    sign_in(user)

    response = idp_client.post("/api/auth/logout")

    assert response.status_code == 200
    assert response.json()["logoutUrl"] == "https://idp.test/end_session"
    assert fake_idp.end_session_calls[-1]["post_logout_redirect_uri"] == settings.zitadel_post_logout_uri
    set_cookie = response.headers.get("set-cookie", "").lower()
    assert settings.session_cookie_name in set_cookie
    assert "max-age=0" in set_cookie or "expires=thu, 01 jan 1970" in set_cookie
    assert client.get("/api/v1/me").status_code == 401


def test_bearer_token_authenticates(idp_client, fake_idp) -> None:
    response = idp_client.get("/api/v1/me", headers={"Authorization": "Bearer cli-token"})

    assert response.status_code == 200
    assert response.json()["email"] == "ada@example.com"
    assert fake_idp.bearer_calls == ["cli-token"]


def test_invalid_bearer_does_not_fall_back_to_the_cookie(
    idp_client, fake_idp, sign_in, make_user, db
) -> None:
    sign_in(make_user(db))

    response = idp_client.get("/api/v1/me", headers={"Authorization": "Bearer bad-token"})

    assert response.status_code == 401
    assert fake_idp.bearer_calls == ["bad-token"]


def test_service_tokens_are_not_enabled_yet(idp_client) -> None:
    response = idp_client.get(
        "/api/v1/me", headers={"Authorization": "Bearer secria_st_placeholder"}
    )
    assert response.status_code == 401
    assert "Service tokens" in response.json()["error"]


def test_bad_authorization_scheme_is_rejected(idp_client) -> None:
    response = idp_client.get("/api/v1/me", headers={"Authorization": "Basic abc"})
    assert response.status_code == 401


def test_profile_update(client, sign_in, make_user, db) -> None:
    sign_in(make_user(db))
    response = client.patch("/api/v1/me", json={"name": "Ada Byron"})
    assert response.status_code == 200
    assert response.json()["name"] == "Ada Byron"


def test_list_and_revoke_sessions(client, sign_in, make_user, db) -> None:
    user = make_user(db)
    sign_in(user)

    listing = client.get("/api/v1/me/sessions")
    assert listing.status_code == 200
    items = listing.json()
    assert len(items) == 1
    assert items[0]["current"] is True
    assert items[0]["kind"] == "web"
    assert isinstance(items[0]["createdAt"], int)

    revoked = client.delete(f"/api/v1/me/sessions/{items[0]['id']}")
    assert revoked.status_code == 204
    set_cookie = revoked.headers.get("set-cookie", "").lower()
    assert settings.session_cookie_name in set_cookie
    assert "max-age=0" in set_cookie or "expires=thu, 01 jan 1970" in set_cookie
    assert client.get("/api/v1/me").status_code == 401
