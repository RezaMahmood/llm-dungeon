"""Administrator-capability enforcement, layered on top of token validation."""

from __future__ import annotations

import azure.functions as func

from backend.api.auth.middleware import authenticate
from backend.api.utils import forbidden_access_not_granted, forbidden_insufficient_permission, unauthorized
from backend.services.allow_list_service import AllowListService
from backend.services.capability_service import CapabilityService


def authorize_admin(
    req: func.HttpRequest,
    allow_list_service: AllowListService | None = None,
    capability_service: CapabilityService | None = None,
) -> tuple[bool, str | None, func.HttpResponse | None]:
    """Returns (is_authorized, user_oid, error_response_or_None)."""
    is_valid, user_oid, _error = authenticate(req)
    if not is_valid:
        return False, None, unauthorized()

    allow_list = allow_list_service or AllowListService()
    if allow_list.get_allow_list_entry(user_oid) is None:
        return False, user_oid, forbidden_access_not_granted()

    capabilities = (capability_service or CapabilityService()).get_user_capabilities(user_oid)
    if "Administrator" not in capabilities:
        return False, user_oid, forbidden_insufficient_permission()

    return True, user_oid, None
