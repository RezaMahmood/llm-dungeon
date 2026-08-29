"""Integration tests for a user holding both Player and Administrator roles."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from backend.api.auth.me import me
from backend.models.provisioned_account_entry import ProvisionedAccountEntry

USER_OID = "550e8400-e29b-41d4-a716-446655440000"


def test_me_for_dual_role_user_returns_both_capabilities(request_factory):
    req = request_factory(method="GET", url="/api/auth/me", token="valid-token")
    entry = ProvisionedAccountEntry(email="dual@example.com", roles=["Player", "Administrator"], objectId=USER_OID)
    account_provisioning_service = MagicMock()
    account_provisioning_service.authorize_sign_in.return_value = (True, entry)

    with patch("backend.api.auth.me.authenticate_with_email", return_value=(True, USER_OID, "dual@example.com", None)):
        response = me(req, account_provisioning_service=account_provisioning_service)

    assert response.status_code == 200
    body = response.get_body().decode()
    assert '"hasPlayer": true' in body or '"hasPlayer":true' in body
    assert '"hasAdministrator": true' in body or '"hasAdministrator":true' in body
