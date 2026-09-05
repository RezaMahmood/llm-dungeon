"""Token validation middleware, applied to all /api/ routes."""

from __future__ import annotations

import logging
from typing import Optional

import azure.functions as func

from backend.services.auth_service import AuthService

logger = logging.getLogger("auth_middleware")


def extract_bearer_token(req: func.HttpRequest) -> Optional[str]:
    # Static Web Apps overwrites the standard `Authorization` header itself
    # when proxying a request to a linked ("bring your own") Function App
    # backend — whatever value the client (this app's own MSAL login) sets
    # never reaches the function (Azure/static-web-apps#158, #275, #34), which
    # made every request look unauthenticated (#212). A custom header name
    # isn't touched by that proxying, so the frontend sends the token there
    # instead (see src/frontend/src/services/authService.js et al.) — but an
    # earlier attempt named it `X-MSAL-Authorization`, which the platform also
    # swallowed (confirmed live: still 401 with a verified-valid token after
    # that rename shipped). Any header starting with `x-ms` (case-insensitive)
    # appears to be reserved/stripped the same way — this name deliberately
    # avoids that prefix.
    header = req.headers.get("X-Custom-Authorization", "")
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
        logger.info("Rejected request: no bearer token provided")
        return False, None, None, "No valid authentication token provided"

    is_valid, user_oid, email, error = service.validate_token(token)
    if not is_valid:
        logger.info("Rejected request: invalid or expired token")
        return False, None, None, "Invalid or expired token"

    return True, user_oid, email, None
