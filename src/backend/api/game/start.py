"""Game start endpoint placeholder — enforces Player capability; full implementation in 008."""

from __future__ import annotations

import logging

import azure.functions as func

from backend.api.auth.middleware import authenticate
from backend.api.utils import forbidden_access_not_granted, forbidden_insufficient_permission, json_response, unauthorized
from backend.services.allow_list_service import AllowListService
from backend.services.capability_service import CapabilityService

logger = logging.getLogger("game.start")


def start(
    req: func.HttpRequest,
    allow_list_service: AllowListService | None = None,
    capability_service: CapabilityService | None = None,
) -> func.HttpResponse:
    is_valid, user_oid, _error = authenticate(req)
    if not is_valid:
        return unauthorized()

    allow_list = allow_list_service or AllowListService()
    if allow_list.get_allow_list_entry(user_oid) is None:
        return forbidden_access_not_granted()

    capabilities = (capability_service or CapabilityService()).get_user_capabilities(user_oid)
    if "Player" not in capabilities:
        return forbidden_insufficient_permission()

    logger.info("Game start placeholder invoked", extra={"user_oid": user_oid})
    return json_response({"status": "success", "message": "Game start not yet implemented"}, status_code=200)
