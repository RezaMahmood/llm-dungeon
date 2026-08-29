"""Unit tests for the auth middleware's token extraction and authentication."""

from __future__ import annotations

from unittest.mock import MagicMock

import azure.functions as func

from backend.api.auth.middleware import authenticate, extract_bearer_token


def test_extract_bearer_token_returns_token(request_factory):
    req = request_factory(token="abc123")
    assert extract_bearer_token(req) == "abc123"


def test_extract_bearer_token_returns_none_when_missing(request_factory):
    req = request_factory()
    assert extract_bearer_token(req) is None


def test_extract_bearer_token_returns_none_for_non_bearer_scheme():
    req = func.HttpRequest(
        method="GET", url="/api/test", headers={"Authorization": "Basic abc123"}, params={}, body=b""
    )
    assert extract_bearer_token(req) is None


def test_authenticate_returns_false_when_no_token(request_factory):
    req = request_factory()
    is_valid, user_oid, error = authenticate(req)
    assert is_valid is False
    assert user_oid is None
    assert error is not None


def test_authenticate_delegates_to_auth_service(request_factory):
    req = request_factory(token="abc123")
    mock_service = MagicMock()
    mock_service.validate_token.return_value = (True, "oid-1", None)

    is_valid, user_oid, error = authenticate(req, auth_service=mock_service)

    assert is_valid is True
    assert user_oid == "oid-1"
    mock_service.validate_token.assert_called_once_with("abc123")


def test_authenticate_returns_generic_message_on_invalid_token(request_factory):
    req = request_factory(token="bad-token")
    mock_service = MagicMock()
    mock_service.validate_token.return_value = (False, None, "signature verification failed")

    is_valid, user_oid, error = authenticate(req, auth_service=mock_service)

    assert is_valid is False
    assert user_oid is None
    assert error == "Invalid or expired token"
