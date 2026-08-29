"""Token validation service — validates JWTs issued by Microsoft Entra ID."""

from __future__ import annotations

import logging
import time
from typing import Optional

import jwt
import requests
from jwt import PyJWKClient
from jwt.exceptions import InvalidTokenError

from backend.config import config

logger = logging.getLogger("auth_service")


class AuthService:
    """Validates Entra ID JWTs: signature, expiry, issuer, and audience.

    Public keys are cached for JWKS_CACHE_SECONDS to avoid a network round-trip
    on every request while still picking up Azure AD key rotations periodically.
    """

    def __init__(self, jwks_uri: Optional[str] = None, issuer: Optional[str] = None, audience: Optional[str] = None) -> None:
        self._jwks_uri = jwks_uri or config.jwks_uri()
        self._issuer = issuer or config.issuer()
        self._audience = audience or config.AZURE_APP_ID
        self._jwk_client: Optional[PyJWKClient] = None
        self._jwk_client_created_at: float = 0.0

    def _get_jwk_client(self) -> PyJWKClient:
        now = time.time()
        if self._jwk_client is None or (now - self._jwk_client_created_at) > config.JWKS_CACHE_SECONDS:
            self._jwk_client = PyJWKClient(self._jwks_uri)
            self._jwk_client_created_at = now
        return self._jwk_client

    def validate_token(self, token_string: str) -> tuple[bool, Optional[str], Optional[str]]:
        """Validate a bearer token.

        Returns (is_valid, user_oid, error_message).
        """
        if not token_string:
            return False, None, "No token provided"

        try:
            jwk_client = self._get_jwk_client()
            signing_key = jwk_client.get_signing_key_from_jwt(token_string)
            decoded = jwt.decode(
                token_string,
                key=signing_key.key,
                algorithms=["RS256"],
                audience=self._audience,
                issuer=self._issuer,
            )
        except InvalidTokenError as exc:
            logger.info("Token validation failed: %s", exc)
            return False, None, str(exc)
        except (requests.RequestException, Exception) as exc:  # noqa: BLE001 - log and deny on any failure
            logger.error("Unexpected error validating token: %s", exc)
            return False, None, "Token validation error"

        user_oid = decoded.get("oid")
        if not user_oid:
            return False, None, "Token missing oid claim"

        return True, user_oid, None
