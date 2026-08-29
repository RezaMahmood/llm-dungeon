"""Unit tests for denial of non-provisioned users (User Story 3)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from backend.api.auth.login import login
from backend.services.account_provisioning_service import AccountProvisioningService

USER_OID = "550e8400-e29b-41d4-a716-446655440000"
EMAIL = "unknown@example.com"


def test_get_by_email_returns_none_for_unprovisioned_email():
    cosmos = MagicMock()
    container = MagicMock()
    cosmos.get_container.return_value = container
    container.read_item.side_effect = Exception("not found")
    service = AccountProvisioningService(cosmos_service=cosmos)

    assert service.get_by_email(EMAIL) is None


def test_authorize_sign_in_returns_false_for_unprovisioned_email():
    cosmos = MagicMock()
    container = MagicMock()
    cosmos.get_container.return_value = container
    container.read_item.side_effect = Exception("not found")
    service = AccountProvisioningService(cosmos_service=cosmos)

    is_authorized, entry = service.authorize_sign_in(EMAIL, USER_OID)

    assert is_authorized is False
    assert entry is None


def test_login_endpoint_returns_403_for_unprovisioned_user(request_factory):
    req = request_factory(method="POST", url="/api/auth/login", token="valid-token")

    account_provisioning_service = MagicMock()
    account_provisioning_service.authorize_sign_in.return_value = (False, None)

    with patch(
        "backend.api.auth.login.authenticate_with_email", return_value=(True, USER_OID, EMAIL, None)
    ):
        response = login(req, account_provisioning_service=account_provisioning_service)

    assert response.status_code == 403
    body = response.get_body().decode()
    assert "Access not granted" in body
    assert USER_OID not in body
