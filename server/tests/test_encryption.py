import os
import uuid

import pytest

from app.services.encryption import (
    DecryptionError,
    MasterKey,
    decrypt_secret,
    encrypt_secret,
    get_master_key,
    new_dek,
    secret_aad,
)


def _master_key() -> MasterKey:
    return MasterKey(key=os.urandom(32), version=1)


def _aad(project_id: uuid.UUID) -> bytes:
    return secret_aad(
        workspace_id=uuid.uuid4(),
        project_id=project_id,
        environment_id=uuid.uuid4(),
        key="DATABASE_URL",
    )


def test_project_key_wrap_round_trip() -> None:
    master = _master_key()
    dek = new_dek()
    project_id = uuid.uuid4()

    wrapped = master.wrap_dek(dek, project_id=project_id, key_version=1)
    assert wrapped != dek
    assert master.unwrap_dek(wrapped, project_id=project_id, key_version=1) == dek


def test_project_key_wrap_is_bound_to_project() -> None:
    master = _master_key()
    wrapped = master.wrap_dek(new_dek(), project_id=uuid.uuid4())

    with pytest.raises(DecryptionError):
        master.unwrap_dek(wrapped, project_id=uuid.uuid4())


def test_project_key_wrap_is_bound_to_version() -> None:
    master = _master_key()
    project_id = uuid.uuid4()
    wrapped = master.wrap_dek(new_dek(), project_id=project_id, key_version=1)

    with pytest.raises(DecryptionError):
        master.unwrap_dek(wrapped, project_id=project_id, key_version=2)


def test_project_key_wrap_is_bound_to_kek_version() -> None:
    master = MasterKey(key=os.urandom(32), version=2)
    project_id = uuid.uuid4()
    wrapped = master.wrap_dek(new_dek(), project_id=project_id)

    with pytest.raises(DecryptionError):
        master.unwrap_dek(wrapped, project_id=project_id, kek_version=1)


def test_tampered_project_key_is_rejected() -> None:
    master = _master_key()
    project_id = uuid.uuid4()
    wrapped = bytearray(master.wrap_dek(new_dek(), project_id=project_id))
    wrapped[-1] ^= 0x01

    with pytest.raises(DecryptionError):
        master.unwrap_dek(bytes(wrapped), project_id=project_id)


def test_malformed_project_key_is_rejected() -> None:
    master = _master_key()
    with pytest.raises(DecryptionError):
        master.unwrap_dek(b"too-short", project_id=uuid.uuid4())


def test_master_key_and_dek_lengths_are_validated() -> None:
    with pytest.raises(ValueError):
        MasterKey(key=b"short")
    with pytest.raises(ValueError):
        MasterKey(key=os.urandom(32), version=0)
    with pytest.raises(ValueError):
        MasterKey(key=os.urandom(32)).wrap_dek(b"short", project_id=uuid.uuid4())


def test_master_key_repr_does_not_leak_the_key() -> None:
    master = _master_key()
    assert "key=" not in repr(master)


def test_secret_round_trip() -> None:
    dek = new_dek()
    aad = _aad(uuid.uuid4())
    value = "postgres://user:pass@example/db?sslmode=require"

    encrypted = encrypt_secret(value, dek, aad=aad)
    assert encrypted.ciphertext != value.encode()
    assert len(encrypted.nonce) == 12
    assert decrypt_secret(encrypted.ciphertext, encrypted.nonce, dek, aad=aad) == value


def test_secret_round_trip_empty_and_unicode() -> None:
    dek = new_dek()
    aad = _aad(uuid.uuid4())

    for value in ["", "pässwörd-✓-🔐", "line one\nline two\n"]:
        encrypted = encrypt_secret(value, dek, aad=aad)
        assert decrypt_secret(encrypted.ciphertext, encrypted.nonce, dek, aad=aad) == value


def test_secret_is_bound_to_aad() -> None:
    dek = new_dek()
    project_id = uuid.uuid4()
    encrypted = encrypt_secret("value", dek, aad=_aad(project_id))

    with pytest.raises(DecryptionError):
        decrypt_secret(encrypted.ciphertext, encrypted.nonce, dek, aad=_aad(project_id))


def test_tampered_secret_is_rejected() -> None:
    dek = new_dek()
    aad = _aad(uuid.uuid4())
    encrypted = encrypt_secret("value", dek, aad=aad)
    tampered = bytearray(encrypted.ciphertext)
    tampered[0] ^= 0x01

    with pytest.raises(DecryptionError):
        decrypt_secret(bytes(tampered), encrypted.nonce, dek, aad=aad)


def test_tampered_nonce_is_rejected() -> None:
    dek = new_dek()
    aad = _aad(uuid.uuid4())
    encrypted = encrypt_secret("value", dek, aad=aad)
    tampered = bytearray(encrypted.nonce)
    tampered[0] ^= 0x01

    with pytest.raises(DecryptionError):
        decrypt_secret(encrypted.ciphertext, bytes(tampered), dek, aad=aad)


def test_fresh_nonce_per_encryption() -> None:
    dek = new_dek()
    aad = _aad(uuid.uuid4())

    first = encrypt_secret("same", dek, aad=aad)
    second = encrypt_secret("same", dek, aad=aad)

    assert first.nonce != second.nonce
    assert first.ciphertext != second.ciphertext


def test_configured_master_key_is_valid() -> None:
    master = get_master_key()
    assert len(master.key) == 32
    assert master.version >= 1
