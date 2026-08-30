"""Admin account provisioning endpoints — add/merge and list Provisioned Account Entries."""

from __future__ import annotations

import json
import logging

import azure.functions as func

from backend.api.admin.middleware import authorize_admin
from backend.api.auth.middleware import authenticate_with_email
from backend.api.utils import error_response, json_response
from backend.config import config
from backend.services.account_provisioning_service import (
    AccountNotFoundError,
    AccountProvisioningService,
    InvalidEmailError,
    RoleRequiredError,
    SeedAdminRemovalError,
    SelfRemovalError,
)

logger = logging.getLogger("admin.accounts")


def _account_summary(entry) -> dict:
    return {
        "email": entry.email,
        "roles": entry.roles,
        "bound": entry.objectId is not None,
        # Client-side convenience only, so the accounts screen can disable the
        # seed administrator's row (T061's server-side check in remove_account
        # is the actual enforcement, per Constitution Principle II).
        "isSeedAdmin": bool(config.SEED_ADMIN_EMAIL) and entry.email == config.SEED_ADMIN_EMAIL.lower(),
    }


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


def remove_account(
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

    _is_valid, _admin_oid, admin_email, _error = authenticate_with_email(req)

    service = account_provisioning_service or AccountProvisioningService()
    try:
        service.remove_account(email, requested_by_email=admin_email, seed_admin_email=config.SEED_ADMIN_EMAIL)
    except SelfRemovalError:
        return error_response(400, "self_removal", "Administrators cannot remove their own account.")
    except SeedAdminRemovalError:
        return error_response(400, "seed_admin_removal", "The seed administrator's account cannot be removed.")
    except AccountNotFoundError:
        return error_response(404, "not_found", "No provisioned account entry exists for this email.")

    logger.info("Account removed", extra={"email": email})
    return json_response({"status": "success"}, status_code=200)
