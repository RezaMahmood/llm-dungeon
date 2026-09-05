"""GET /api/auth/me — return the current user's identity and capabilities."""

from __future__ import annotations

import logging

import azure.functions as func

from backend.api.auth.middleware import authenticate_with_email
from backend.api.utils import forbidden_access_not_granted, json_response, unauthorized
from backend.services.account_provisioning_service import AccountProvisioningService

logger = logging.getLogger("auth.me")


def me(
    req: func.HttpRequest,
    account_provisioning_service: AccountProvisioningService | None = None,
) -> func.HttpResponse:
    is_valid, user_oid, email, error = authenticate_with_email(req)
    if not is_valid:
        logger.info("Authentication failed: %s", error)
        return unauthorized(error)

    service = account_provisioning_service or AccountProvisioningService()
    is_authorized, entry = service.authorize_sign_in(email, user_oid)
    if not is_authorized:
        logger.info("Access denied: no provisioned account or objectId mismatch", extra={"user_oid": user_oid})
        return forbidden_access_not_granted()

    return json_response(
        {
            "status": "success",
            "user": {"oid": user_oid, "email": entry.email},
            "capabilities": {
                "hasPlayer": "Player" in entry.roles,
                "hasAdministrator": "Administrator" in entry.roles,
            },
        },
        status_code=200,
    )
