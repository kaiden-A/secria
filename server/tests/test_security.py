import base64
import hashlib
import time
from datetime import UTC, datetime

from app.services import security
from app.utils import from_ms, local_path, to_ms


def test_signed_payload_round_trip() -> None:
    payload = {"state": "state-1", "next": "/w/acme", "iat": int(time.time())}
    signed = security.sign_payload(payload, "secret")
    assert security.unsign_payload(signed, "secret", max_age=600) == payload


def test_signed_payload_rejects_tampering_and_wrong_secret() -> None:
    signed = security.sign_payload({"state": "state-1", "iat": int(time.time())}, "secret")
    tampered = signed[:-1] + ("A" if signed[-1] != "A" else "B")
    assert security.unsign_payload(tampered, "secret", max_age=600) is None
    assert security.unsign_payload(signed, "other-secret", max_age=600) is None


def test_signed_payload_expires() -> None:
    signed = security.sign_payload({"iat": int(time.time()) - 700}, "secret")
    assert security.unsign_payload(signed, "secret", max_age=600) is None


def test_pkce_pair_is_s256() -> None:
    verifier, challenge = security.create_pkce_pair()
    expected = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    )
    assert challenge == expected
    assert 43 <= len(verifier) <= 128


def test_token_hashing_and_constant_time_comparison() -> None:
    token = "raw-token"
    digest = security.hash_token(token)
    assert len(digest) == 64
    assert security.token_matches(token, digest) is True
    assert security.token_matches("other-token", digest) is False


def test_local_path_only_allows_same_site_paths() -> None:
    assert local_path("/w/acme") == "/w/acme"
    assert local_path("//evil.example") == "/"
    assert local_path("https://evil.example") == "/"
    assert local_path(None) == "/"
    assert local_path(None, default="/settings") == "/settings"


def test_millisecond_round_trip() -> None:
    value = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
    millis = to_ms(value)
    assert isinstance(millis, int)
    assert from_ms(millis) == value
    assert to_ms(None) is None
    assert from_ms(None) is None
