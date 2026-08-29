"""Game start endpoint placeholder — enforces Player capability; full implementation in 008."""

from __future__ import annotations

import logging

import azure.functions as func

from backend.api.auth.middleware import authenticate_with_email
from backend.api.utils import forbidden_access_not_granted, forbidden_insufficient_permission, json_response, unauthorized
from backend.services.account_provisioning_service import AccountProvisioningService

logger = logging.getLogger("game.start")


def start(
    req: func.HttpRequest,
    account_provisioning_service: AccountProvisioningService | None = None,
) -> func.HttpResponse:
    is_valid, user_oid, email, _error = authenticate_with_email(req)
    if not is_valid:
        return unauthorized()

    service = account_provisioning_service or AccountProvisioningService()
    is_authorized, entry = service.authorize_sign_in(email, user_oid)
    if not is_authorized:
        return forbidden_access_not_granted()

    if "Player" not in entry.roles:
        return forbidden_insufficient_permission()

    logger.info("Game start placeholder invoked", extra={"user_oid": user_oid})
    return json_response({"status": "success", "message": "Game start not yet implemented"}, status_code=200)
