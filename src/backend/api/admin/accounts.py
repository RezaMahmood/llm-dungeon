"""Admin account provisioning endpoints — add/merge and list Provisioned Account Entries."""

from __future__ import annotations

import json
import logging

import azure.functions as func

from backend.api.admin.middleware import authorize_admin
from backend.api.auth.middleware import authenticate_with_email
from backend.api.utils import error_response, json_response
from backend.services.account_provisioning_service import (
    AccountProvisioningService,
    InvalidEmailError,
    RoleRequiredError,
)

logger = logging.getLogger("admin.accounts")


def _account_summary(entry) -> dict:
    return {"email": entry.email, "roles": entry.roles, "bound": entry.objectId is not None}


def add_account(
    req: func.HttpRequest,
    account_provisioning_service: AccountProvisioningService | None = None,
) -> func.HttpResponse:
    is_authorized, _user_oid, error = authorize_admin(req)
    if not is_authorized:
        return error

    try:
        body = json.loads(req.get_body() or b"{}")
    except (ValueError, json.JSONDecodeError):
        body = {}

    email = body.get("email", "")
    roles = body.get("roles", [])

    # authorize_admin already validated the token; re-reading the email claim here
    # avoids widening authorize_admin's shared return shape (kept stable for
    # admin/stories.py, per T007).
    _is_valid, _admin_oid, admin_email, _error = authenticate_with_email(req)

    service = account_provisioning_service or AccountProvisioningService()
    try:
        entry = service.add_or_merge(email, roles, added_by=admin_email)
    except RoleRequiredError:
        return error_response(400, "role_required", "Select at least one role (Player and/or Administrator).")
    except InvalidEmailError:
        return error_response(400, "invalid_email", "Enter a valid email address.")

    logger.info("Account added or merged", extra={"email": entry.email, "roles": sorted(entry.roles)})
    return json_response({"status": "success", "account": _account_summary(entry)}, status_code=200)


def list_accounts(
    req: func.HttpRequest,
    account_provisioning_service: AccountProvisioningService | None = None,
) -> func.HttpResponse:
    is_authorized, _user_oid, error = authorize_admin(req)
    if not is_authorized:
        return error

    service = account_provisioning_service or AccountProvisioningService()
    entries = service.list_all()

    return json_response(
        {"status": "success", "accounts": [_account_summary(entry) for entry in entries]},
        status_code=200,
    )
