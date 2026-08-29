"""GET /api/auth/me — return the current user's identity and capabilities."""

from __future__ import annotations

import logging

import azure.functions as func

from backend.api.auth.middleware import authenticate
from backend.api.utils import forbidden_access_not_granted, json_response, unauthorized
from backend.services.allow_list_service import AllowListService
from backend.services.capability_service import CapabilityService

logger = logging.getLogger("auth.me")


def me(
    req: func.HttpRequest,
    allow_list_service: AllowListService | None = None,
    capability_service: CapabilityService | None = None,
) -> func.HttpResponse:
    is_valid, user_oid, _error = authenticate(req)
    if not is_valid:
        return unauthorized()

    allow_list = allow_list_service or AllowListService()
    entry = allow_list.get_allow_list_entry(user_oid)
    if entry is None:
        logger.info("Access denied: user not on allow-list", extra={"user_oid": user_oid})
        return forbidden_access_not_granted()

    capabilities = (capability_service or CapabilityService()).get_user_capabilities(user_oid)

    return json_response(
        {
            "status": "success",
            "user": {"oid": user_oid, "email": entry.email},
            "capabilities": {
                "hasPlayer": "Player" in capabilities,
                "hasAdministrator": "Administrator" in capabilities,
            },
        },
        status_code=200,
    )
