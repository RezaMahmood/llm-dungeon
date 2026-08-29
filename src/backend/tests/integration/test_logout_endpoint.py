"""Integration tests for POST /api/auth/logout."""

from __future__ import annotations

from unittest.mock import patch

from backend.api.auth.logout import logout


def test_logout_with_valid_token_returns_200(request_factory):
    req = request_factory(method="POST", url="/api/auth/logout", token="valid-token")

    with patch("backend.api.auth.logout.authenticate", return_value=(True, "some-oid", None)):
        response = logout(req)

    assert response.status_code == 200
    assert "Logged out successfully" in response.get_body().decode()


def test_logout_without_token_returns_401(request_factory):
    req = request_factory(method="POST", url="/api/auth/logout")

    response = logout(req)

    assert response.status_code == 401
