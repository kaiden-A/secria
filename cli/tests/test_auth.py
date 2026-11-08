import base64
import json
import time

import pytest

from secria_cli import auth
from secria_cli.errors import AuthError


def _jwt(payload: dict) -> str:
    def part(data: dict) -> str:
        raw = json.dumps(data, separators=(",", ":")).encode()
        return base64.urlsafe_b64encode(raw).decode().rstrip("=")

    return f"{part({'alg': 'none'})}.{part(payload)}.signature"


def test_token_store_file_fallback(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("SECRIA_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("SECRIA_API_URL", "https://api.test")
    monkeypatch.setenv("SECRIA_DISABLE_KEYRING", "1")
    store = auth.TokenStore()
    assert store.get() is None
    store.set({"access_token": "a", "id_token": "i", "expires_at": 0})
    assert store.get() == {"access_token": "a", "id_token": "i", "expires_at": 0}
    assert (tmp_path / "credentials-api.test.json").is_file()
    store.clear()
    assert store.get() is None


def test_token_store_is_scoped_per_host(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("SECRIA_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("SECRIA_DISABLE_KEYRING", "1")
    one = auth.TokenStore("https://one.example.com")
    two = auth.TokenStore("https://two.example.com")
    one.set({"access_token": "one"})
    two.set({"access_token": "two"})
    assert one.get() == {"access_token": "one"}
    assert two.get() == {"access_token": "two"}
    assert (tmp_path / "credentials-one.example.com.json").is_file()
    assert (tmp_path / "credentials-two.example.com.json").is_file()


def test_decode_claims() -> None:
    token = _jwt({"sub": "sub-1", "email": "ada@example.com"})
    claims = auth.decode_claims(token)
    assert claims["sub"] == "sub-1"
    assert claims["email"] == "ada@example.com"
    assert auth.decode_claims("not-a-token") == {}


def test_get_token_prefers_service_token(monkeypatch) -> None:
    monkeypatch.setenv("SECRIA_TOKEN", "secria_st_test")
    assert auth.get_token() == "secria_st_test"


def test_get_token_requires_login(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("SECRIA_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("SECRIA_DISABLE_KEYRING", "1")
    monkeypatch.delenv("SECRIA_TOKEN", raising=False)
    with pytest.raises(AuthError):
        auth.get_token()


def test_expired_token_without_refresh_requires_login(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("SECRIA_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("SECRIA_DISABLE_KEYRING", "1")
    monkeypatch.delenv("SECRIA_TOKEN", raising=False)
    auth.TokenStore().set(
        {
            "access_token": "a",
            "id_token": "i",
            "refresh_token": None,
            "expires_at": int(time.time()) - 10,
        }
    )
    with pytest.raises(AuthError):
        auth.get_token()
