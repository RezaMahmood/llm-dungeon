"""Standard, generic error responses. No response reveals account existence."""

from __future__ import annotations

import json

import azure.functions as func


def json_response(body: dict, status_code: int) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps(body),
        status_code=status_code,
        mimetype="application/json",
        headers={
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


def error_response(status_code: int, error: str, message: str) -> func.HttpResponse:
    return json_response({"error": error, "message": message}, status_code)


def unauthorized(message: str = "No valid authentication token provided") -> func.HttpResponse:
    return error_response(401, "unauthenticated", message)


def forbidden() -> func.HttpResponse:
    return forbidden_access_not_granted()


def forbidden_access_not_granted() -> func.HttpResponse:
    """Identical generic message for non-allow-listed users and capability-gated
    endpoints — prevents account enumeration."""
    return error_response(403, "access_denied", "Access not granted")


def forbidden_insufficient_permission() -> func.HttpResponse:
    return error_response(403, "insufficient_permission", "You do not have permission to access this resource")


def server_error(message: str = "An error occurred") -> func.HttpResponse:
    return error_response(500, "internal_error", message)
