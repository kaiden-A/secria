import base64
import time
from collections.abc import Iterator

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app.services.zitadel import ZitadelClient, ZitadelError


def _b64url_uint(value: int) -> str:
    raw = value.to_bytes((value.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


@pytest.fixture
def signing() -> Iterator[tuple[ZitadelClient, rsa.RSAPrivateKey]]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    numbers = private_key.public_key().public_numbers()
    jwks = {
        "keys": [
            {
                "kty": "RSA",
                "kid": "test-kid",
                "use": "sig",
                "alg": "RS256",
                "n": _b64url_uint(numbers.n),
                "e": _b64url_uint(numbers.e),
            }
        ]
    }
    http = httpx.Client()
    client = ZitadelClient(
        issuer="https://idp.test",
        client_id="web-client",
        http=http,
        api_audience="api-audience",
        cli_client_id="cli-client",
        jwks=jwks,
    )
    client._discovery = {
        "authorization_endpoint": "https://idp.test/authorize",
        "token_endpoint": "https://idp.test/token",
        "jwks_uri": "https://idp.test/keys",
        "end_session_endpoint": "https://idp.test/logout",
        "id_token_signing_alg_values_supported": ["RS256"],
    }
    try:
        yield client, private_key
    finally:
        http.close()


def _token(private_key: rsa.RSAPrivateKey, **overrides: object) -> str:
    now = int(time.time())
    claims: dict[str, object] = {
        "iss": "https://idp.test",
        "sub": "sub-1",
        "aud": "web-client",
        "iat": now,
        "exp": now + 300,
        "email": "ada@example.com",
        "email_verified": True,
        "name": "Ada",
        "nonce": "nonce-1",
    }
    claims.update(overrides)
    return jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": "test-kid"})


def test_verify_id_token_checks_nonce(signing) -> None:
    client, private_key = signing
    claims = client.verify_id_token(_token(private_key), nonce="nonce-1")
    assert claims["sub"] == "sub-1"
    assert claims["email_verified"] is True

    with pytest.raises(ZitadelError):
        client.verify_id_token(_token(private_key), nonce="wrong")


def test_verify_id_token_rejects_wrong_audience_and_expiry(signing) -> None:
    client, private_key = signing
    with pytest.raises(ZitadelError):
        client.verify_id_token(_token(private_key, aud="other-client"), nonce="nonce-1")
    with pytest.raises(ZitadelError):
        client.verify_id_token(
            _token(private_key, exp=int(time.time()) - 120),
            nonce="nonce-1",
        )


def test_verify_bearer_accepts_client_and_api_audiences(signing) -> None:
    client, private_key = signing
    assert client.verify_bearer(_token(private_key))["sub"] == "sub-1"
    assert client.verify_bearer(_token(private_key, aud="api-audience"))["sub"] == "sub-1"
    assert client.verify_bearer(_token(private_key, aud="cli-client"))["sub"] == "sub-1"

    with pytest.raises(ZitadelError):
        client.verify_bearer(_token(private_key, aud="wrong-audience"))


def test_authorize_url_contains_pkce_and_state(signing) -> None:
    client, _private_key = signing
    url = client.authorize_url(
        state="state-1",
        nonce="nonce-1",
        code_challenge="challenge-1",
        redirect_uri="http://localhost:3000/api/auth/callback",
        login_hint="ada@example.com",
        prompt="login",
    )
    assert url.startswith("https://idp.test/authorize?")
    assert "client_id=web-client" in url
    assert "code_challenge=challenge-1" in url
    assert "code_challenge_method=S256" in url
    assert "state=state-1" in url
    assert "login_hint=ada%40example.com" in url
    assert "prompt=login" in url


def test_end_session_url_contains_client_id(signing) -> None:
    client, _private_key = signing
    url = client.end_session_url(post_logout_redirect_uri="http://localhost:3000/login")
    assert url.startswith("https://idp.test/logout?")
    assert "client_id=web-client" in url
    assert "post_logout_redirect_uri=http%3A%2F%2Flocalhost%3A3000%2Flogin" in url
