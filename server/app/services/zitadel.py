"""Minimal, explicit OIDC client.

The web app is a PKCE public client: the code exchange happens server-side, so
the verifier never leaves this process. The same client validates CLI bearer
tokens via JWKS. No client secret exists.
"""

from dataclasses import dataclass, field
from functools import lru_cache
from urllib.parse import urlencode

import httpx
import jwt

SCOPE = "openid profile email"

# The IdP's clock is never exactly ours: a token minted "now" can arrive with an
# iat a second or two in the future and would otherwise fail validation.
CLOCK_SKEW_SECONDS = 60


class ZitadelError(RuntimeError):
    pass


@lru_cache(maxsize=8)
def _discovery_cached(issuer: str) -> dict:
    response = httpx.get(f"{issuer.rstrip('/')}/.well-known/openid-configuration", timeout=10.0)
    response.raise_for_status()
    return dict(response.json())


@lru_cache(maxsize=8)
def _jwks_cached(issuer: str) -> dict:
    discovery = _discovery_cached(issuer)
    response = httpx.get(discovery["jwks_uri"], timeout=10.0)
    response.raise_for_status()
    return dict(response.json())


@dataclass
class ZitadelClient:
    issuer: str
    client_id: str
    http: httpx.Client
    api_audience: str | None = None
    jwks: dict | None = None  # test seam: skip fetching the key set
    _discovery: dict | None = field(default=None, init=False, repr=False)

    def discovery(self) -> dict:
        if self._discovery is not None:
            return self._discovery
        try:
            self._discovery = _discovery_cached(self.issuer.rstrip("/"))
        except httpx.HTTPError as exc:
            raise ZitadelError("The identity provider could not be reached.") from exc
        return self._discovery

    def authorize_url(
        self,
        *,
        state: str,
        nonce: str,
        code_challenge: str,
        redirect_uri: str,
        login_hint: str | None = None,
        prompt: str | None = None,
    ) -> str:
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "scope": SCOPE,
            "redirect_uri": redirect_uri,
            "state": state,
            "nonce": nonce,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        if login_hint:
            params["login_hint"] = login_hint
        if prompt:
            params["prompt"] = prompt
        return f"{self.discovery()['authorization_endpoint']}?{urlencode(params)}"

    def exchange_code(self, *, code: str, code_verifier: str, redirect_uri: str) -> dict:
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": self.client_id,
            "code_verifier": code_verifier,
        }
        try:
            response = self.http.post(self.discovery()["token_endpoint"], data=payload)
        except httpx.HTTPError as exc:
            raise ZitadelError("The identity provider could not be reached.") from exc
        if response.status_code >= 400:
            raise ZitadelError(f"token exchange failed ({response.status_code})")
        return response.json()

    def verify_id_token(self, id_token: str, *, nonce: str) -> dict:
        claims = self._decode(id_token, audience=self.client_id)
        if claims.get("nonce") != nonce:
            raise ZitadelError("nonce mismatch")
        return claims

    def verify_bearer(self, token: str) -> dict:
        """Validate a CLI bearer JWT.

        The CLI sends the ID token from the device flow by default, whose
        audience is the client ID. If ZITADEL_API_AUDIENCE is configured, an
        access token for that audience is accepted too.
        """
        audiences = [self.client_id]
        if self.api_audience and self.api_audience not in audiences:
            audiences.append(self.api_audience)
        return self._decode(token, audience=audiences)

    def end_session_url(
        self, *, id_token_hint: str | None = None, post_logout_redirect_uri: str | None = None
    ) -> str:
        endpoint = self.discovery()["end_session_endpoint"]
        params = {"client_id": self.client_id}
        if id_token_hint:
            params["id_token_hint"] = id_token_hint
        if post_logout_redirect_uri:
            params["post_logout_redirect_uri"] = post_logout_redirect_uri
        return f"{endpoint}?{urlencode(params)}"

    def _decode(self, token: str, *, audience: str | list[str]) -> dict:
        key, algorithms = self._signing_key(token)
        try:
            claims = jwt.decode(
                token,
                key,
                algorithms=algorithms,
                audience=audience,
                issuer=self.issuer.rstrip("/"),
                options={"require": ["exp", "iat", "sub", "aud", "iss"]},
                leeway=CLOCK_SKEW_SECONDS,
            )
        except jwt.PyJWTError as exc:
            raise ZitadelError("token rejected") from exc
        return claims

    def _signing_key(self, token: str) -> tuple[jwt.PyJWK, list[str]]:
        if self.jwks is not None:
            key_set = self.jwks
        else:
            try:
                key_set = _jwks_cached(self.issuer.rstrip("/"))
            except httpx.HTTPError as exc:
                raise ZitadelError("The identity provider keys could not be fetched.") from exc
        try:
            kid = jwt.get_unverified_header(token).get("kid")
        except jwt.PyJWTError as exc:
            raise ZitadelError("Malformed token.") from exc
        try:
            parsed = jwt.PyJWKSet.from_dict(key_set)
            key = parsed[kid] if kid else parsed.keys[0]
        except (jwt.PyJWTError, KeyError, IndexError) as exc:
            raise ZitadelError("Unknown signing key.") from exc

        algorithms = self.discovery().get("id_token_signing_alg_values_supported") or ["RS256"]
        usable = [alg for alg in algorithms if alg != "none"]
        if not usable:
            raise ZitadelError("The identity provider has no usable signing algorithm.")
        return key, usable
