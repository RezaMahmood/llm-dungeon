"""Token validation middleware, applied to all /api/ routes."""

from __future__ import annotations

import logging
from typing import Optional

import azure.functions as func

from backend.services.auth_service import AuthService

logger = logging.getLogger("auth_middleware")


def extract_bearer_token(req: func.HttpRequest) -> Optional[str]:
    header = req.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    return header[len("Bearer "):].strip()


def authenticate(req: func.HttpRequest, auth_service: Optional[AuthService] = None) -> tuple[bool, Optional[str], Optional[str]]:
    """Validate the request's bearer token.

    Returns (is_valid, user_oid, error_message). Callers attach user_oid to their
    own request-scoped context for use by the endpoint handler.
    """
    is_valid, user_oid, _email, error = _validate(req, auth_service)
    if not is_valid:
        return False, None, error
    return True, user_oid, None


def authenticate_with_email(
    req: func.HttpRequest, auth_service: Optional[AuthService] = None
) -> tuple[bool, Optional[str], Optional[str], Optional[str]]:
    """Validate the request's bearer token, also returning the token's email claim.

    Returns (is_valid, user_oid, email, error_message).
    """
    return _validate(req, auth_service)


def _validate(
    req: func.HttpRequest, auth_service: Optional[AuthService] = None
) -> tuple[bool, Optional[str], Optional[str], Optional[str]]:
    service = auth_service or AuthService()
    token = extract_bearer_token(req)
    if not token:
        return False, None, None, "No valid authentication token provided"

    is_valid, user_oid, email, error = service.validate_token(token)
    if not is_valid:
        logger.info("Rejected request: invalid or expired token")
        return False, None, None, "Invalid or expired token"

    return True, user_oid, email, None
