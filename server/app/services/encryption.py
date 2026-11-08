"""Envelope encryption for Secria.

KEK (master key, env only) wraps a random per-project DEK. Secret values are
encrypted with that DEK using AES-256-GCM. Every ciphertext is bound to its
workspace/project/environment/key through the AAD, so a value cannot be moved
between secrets.

Nothing in this module logs or stringifies plaintext.
"""

import os
from dataclasses import dataclass, field
from functools import lru_cache
from uuid import UUID

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

DEK_BYTES = 32
KEK_BYTES = 32
NONCE_BYTES = 12
GCM_TAG_BYTES = 16


class EncryptionError(RuntimeError):
    """Base class for encryption failures; messages never contain plaintext."""


class DecryptionError(EncryptionError):
    """The ciphertext could not be authenticated or decoded."""


def new_dek() -> bytes:
    return os.urandom(DEK_BYTES)


def secret_aad(
    *,
    workspace_id: UUID | str,
    project_id: UUID | str,
    environment_id: UUID | str,
    key: str,
) -> bytes:
    """The exact binding used for every secret value."""
    return f"{workspace_id}:{project_id}:{environment_id}:{key}".encode()


def _dek_aad(*, project_id: UUID | str, key_version: int, kek_version: int) -> bytes:
    return f"secria:dek:{project_id}:{key_version}:{kek_version}".encode()


@dataclass(frozen=True)
class MasterKey:
    """The KEK and its version.

    The version is stored on project_keys so a rotation can select the right
    wrapping key. The MVP keeps one key in memory; the runbook in docs/security
    covers a manual re-wrap.
    """

    key: bytes = field(repr=False)
    version: int = 1

    def __post_init__(self) -> None:
        if len(self.key) != KEK_BYTES:
            raise ValueError("The master key must be exactly 32 bytes.")
        if self.version < 1:
            raise ValueError("The master key version must be positive.")

    def wrap_dek(self, dek: bytes, *, project_id: UUID | str, key_version: int = 1) -> bytes:
        _require_dek(dek)
        nonce = os.urandom(NONCE_BYTES)
        aad = _dek_aad(project_id=project_id, key_version=key_version, kek_version=self.version)
        ciphertext = AESGCM(self.key).encrypt(nonce, dek, aad)
        return nonce + ciphertext

    def unwrap_dek(
        self,
        blob: bytes,
        *,
        project_id: UUID | str,
        key_version: int = 1,
        kek_version: int | None = None,
    ) -> bytes:
        version = self.version if kek_version is None else kek_version
        if version != self.version:
            raise DecryptionError("That master-key version is not loaded.")
        if len(blob) < NONCE_BYTES + DEK_BYTES + GCM_TAG_BYTES:
            raise DecryptionError("The wrapped project key is malformed.")
        nonce, ciphertext = blob[:NONCE_BYTES], blob[NONCE_BYTES:]
        aad = _dek_aad(project_id=project_id, key_version=key_version, kek_version=version)
        try:
            dek = AESGCM(self.key).decrypt(nonce, ciphertext, aad)
        except InvalidTag as exc:
            raise DecryptionError("The wrapped project key could not be authenticated.") from exc
        _require_dek(dek)
        return dek


@dataclass(frozen=True)
class EncryptedSecret:
    ciphertext: bytes
    nonce: bytes


def encrypt_secret(value: str, dek: bytes, *, aad: bytes) -> EncryptedSecret:
    _require_dek(dek)
    nonce = os.urandom(NONCE_BYTES)
    ciphertext = AESGCM(dek).encrypt(nonce, value.encode("utf-8"), aad)
    return EncryptedSecret(ciphertext=ciphertext, nonce=nonce)


def decrypt_secret(ciphertext: bytes, nonce: bytes, dek: bytes, *, aad: bytes) -> str:
    _require_dek(dek)
    if len(nonce) != NONCE_BYTES:
        raise DecryptionError("The secret nonce is malformed.")
    if len(ciphertext) < GCM_TAG_BYTES:
        raise DecryptionError("The secret ciphertext is malformed.")
    try:
        raw = AESGCM(dek).decrypt(nonce, ciphertext, aad)
    except InvalidTag as exc:
        raise DecryptionError("The secret could not be authenticated.") from exc
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DecryptionError("The secret is not valid UTF-8.") from exc


def _require_dek(dek: bytes) -> None:
    if len(dek) != DEK_BYTES:
        raise ValueError("A project key must be exactly 32 bytes.")


@lru_cache
def get_master_key() -> MasterKey:
    """The configured KEK. Cached for the process; tests construct their own."""
    from ..config import get_settings

    settings = get_settings()
    return MasterKey(key=settings.master_key_bytes, version=settings.secria_master_key_version)
