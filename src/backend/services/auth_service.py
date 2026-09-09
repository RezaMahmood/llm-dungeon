"""Token validation service — validates JWTs issued by Microsoft Entra ID."""

from __future__ import annotations

import logging
import threading
import time
from typing import Iterable, Optional, Union

import jwt
import requests
from jwt import PyJWKClient
from jwt.exceptions import InvalidTokenError

from backend.config import config

logger = logging.getLogger("auth_service")

# The signing-key cache has to outlive the request to be a cache at all. AuthService is
# constructed per request by the auth middleware, so a PyJWKClient held only on the
# instance meant JWKS_CACHE_SECONDS could never elapse and every single request re-fetched
# https://login.microsoftonline.com/common/discovery/v2.0/keys (#286). Keyed by URI so a
# test pointing at its own endpoint cannot poison the real one.
_jwk_clients: dict[str, tuple[PyJWKClient, float]] = {}
_jwk_clients_lock = threading.Lock()


def _shared_jwk_client(jwks_uri: str) -> PyJWKClient:
    now = time.time()
    with _jwk_clients_lock:
        cached = _jwk_clients.get(jwks_uri)
        if cached is None or (now - cached[1]) > config.JWKS_CACHE_SECONDS:
            cached = (PyJWKClient(jwks_uri), now)
            _jwk_clients[jwks_uri] = cached
        return cached[0]


class AuthService:
    """Validates Entra ID JWTs: signature, expiry, issuer, and audience.

    Public keys are cached for JWKS_CACHE_SECONDS to avoid a network round-trip
    on every request while still picking up Azure AD key rotations periodically.
    """

    def __init__(
        self,
        jwks_uri: Optional[str] = None,
        issuer: Optional[Union[str, Iterable[str]]] = None,
        audience: Optional[Union[str, Iterable[str]]] = None,
    ) -> None:
        self._jwks_uri = jwks_uri or config.jwks_uri()
        # Accept either a single issuer (tests) or an iterable of accepted
        # issuers; defaults to every issuer this app's accounts can present
        # (see config.valid_issuers — this app supports personal Microsoft
        # accounts, not just this org's tenant).
        if issuer is None:
            self._valid_issuers: tuple[str, ...] = config.valid_issuers()
        elif isinstance(issuer, str):
            self._valid_issuers = (issuer,)
        else:
            self._valid_issuers = tuple(issuer)
        # Accept either a single audience (tests) or an iterable of accepted
        # audiences; defaults to every audience form Entra ID may stamp on
        # this app's own access tokens (see config.valid_audiences).
        if audience is None:
            self._valid_audiences: tuple[str, ...] = config.valid_audiences()
        elif isinstance(audience, str):
            self._valid_audiences = (audience,)
        else:
            self._valid_audiences = tuple(audience)
        self._jwk_client: Optional[PyJWKClient] = None
        self._jwk_client_created_at: float = 0.0

    def _get_jwk_client(self) -> PyJWKClient:
        # An instance-level client stays an explicit override (the tests set one directly);
        # everything else comes from the process-wide cache, which is the only place the
        # JWKS_CACHE_SECONDS window can actually be observed.
        if self._jwk_client is not None and (time.time() - self._jwk_client_created_at) <= config.JWKS_CACHE_SECONDS:
            return self._jwk_client
        return _shared_jwk_client(self._jwks_uri)

    def validate_token(self, token_string: str) -> tuple[bool, Optional[str], Optional[str], Optional[str]]:
        """Validate a bearer token.

        Returns (is_valid, user_oid, email, error_message).
        """
        if not token_string:
            return False, None, None, "No token provided"

        try:
            jwk_client = self._get_jwk_client()
            signing_key = jwk_client.get_signing_key_from_jwt(token_string)
            decoded = jwt.decode(
                token_string,
                key=signing_key.key,
                algorithms=["RS256"],
                audience=list(self._valid_audiences),
                # Not passed to jwt.decode: PyJWT's built-in issuer check only
                # accepts a single value, but this app must accept tokens
                # from more than one issuer (org tenant + MSA consumers
                # tenant) — validated manually below instead.
            )
        except InvalidTokenError as exc:
            logger.info("Token validation failed: %s", exc)
            return False, None, None, str(exc)
        except (requests.RequestException, Exception) as exc:  # noqa: BLE001 - log and deny on any failure
            logger.error("Unexpected error validating token: %s", exc)
            return False, None, None, "Token validation error"

        if decoded.get("iss") not in self._valid_issuers:
            logger.info("Token validation failed: untrusted issuer %r", decoded.get("iss"))
            return False, None, None, "Token issued by an untrusted issuer"

        user_oid = decoded.get("oid")
        if not user_oid:
            return False, None, None, "Token missing oid claim"

        email = decoded.get("email")
        return True, user_oid, email, None
