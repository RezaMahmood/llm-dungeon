"""Player-capability enforcement, layered on top of token validation. Mirrors
backend.api.admin.middleware.authorize_admin (006-adventure-and-character-setup
research.md Decision 3)."""

from __future__ import annotations

import azure.functions as func

from backend.api.auth.middleware import authenticate_with_email
from backend.api.utils import forbidden_access_not_granted, forbidden_insufficient_permission, unauthorized
from backend.services.account_provisioning_service import AccountProvisioningService


def authorize_player(
    req: func.HttpRequest,
    account_provisioning_service: AccountProvisioningService | None = None,
) -> tuple[bool, str | None, func.HttpResponse | None]:
    """Returns (is_authorized, user_oid, error_response_or_None)."""
    is_valid, user_oid, email, _error = authenticate_with_email(req)
    if not is_valid:
        return False, None, unauthorized()

    service = account_provisioning_service or AccountProvisioningService()
    is_authorized, entry = service.authorize_sign_in(email, user_oid)
    if not is_authorized:
        return False, user_oid, forbidden_access_not_granted()

    if "Player" not in entry.roles:
        return False, user_oid, forbidden_insufficient_permission()

    return True, user_oid, None
