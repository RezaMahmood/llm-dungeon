"""POST /api/auth/login — validate token, resolve provisioned account, return capabilities."""

from __future__ import annotations

import logging

import azure.functions as func

from backend.api.auth.middleware import authenticate_with_email
from backend.api.utils import forbidden_access_not_granted, json_response, unauthorized
from backend.services.account_provisioning_service import AccountProvisioningService

logger = logging.getLogger("auth.login")


def login(
    req: func.HttpRequest,
    account_provisioning_service: AccountProvisioningService | None = None,
) -> func.HttpResponse:
    is_valid, user_oid, email, _error = authenticate_with_email(req)
    if not is_valid:
        return unauthorized()

    service = account_provisioning_service or AccountProvisioningService()
    is_authorized, entry = service.authorize_sign_in(email, user_oid)
    if not is_authorized:
        logger.info("Login denied: no provisioned account or objectId mismatch", extra={"user_oid": user_oid})
        return forbidden_access_not_granted()

    logger.info("Login succeeded", extra={"user_oid": user_oid, "roles": sorted(entry.roles)})

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
