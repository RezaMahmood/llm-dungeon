"""Unit tests for the auth middleware's token extraction and authentication."""

from __future__ import annotations

from unittest.mock import MagicMock

import azure.functions as func

from backend.api.auth.middleware import authenticate, authenticate_with_email, extract_bearer_token


def test_extract_bearer_token_returns_token(request_factory):
    req = request_factory(token="abc123")
    assert extract_bearer_token(req) == "abc123"


def test_extract_bearer_token_returns_none_when_missing(request_factory):
    req = request_factory()
    assert extract_bearer_token(req) is None


def test_extract_bearer_token_returns_none_for_non_bearer_scheme():
    req = func.HttpRequest(
        method="GET", url="/api/test", headers={"X-MSAL-Authorization": "Basic abc123"}, params={}, body=b""
    )
    assert extract_bearer_token(req) is None


def test_extract_bearer_token_ignores_the_authorization_header():
    """Static Web Apps overwrites `Authorization` itself when proxying to this
    linked Function App backend (#212), so a token placed there instead of
    the custom header must not be picked up.
    """
    req = func.HttpRequest(
        method="GET", url="/api/test", headers={"Authorization": "Bearer abc123"}, params={}, body=b""
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
    mock_service.validate_token.return_value = (True, "oid-1", "user@example.com", None)

    is_valid, user_oid, error = authenticate(req, auth_service=mock_service)

    assert is_valid is True
    assert user_oid == "oid-1"
    mock_service.validate_token.assert_called_once_with("abc123")


def test_authenticate_returns_generic_message_on_invalid_token(request_factory):
    req = request_factory(token="bad-token")
    mock_service = MagicMock()
    mock_service.validate_token.return_value = (False, None, None, "signature verification failed")

    is_valid, user_oid, error = authenticate(req, auth_service=mock_service)

    assert is_valid is False
    assert user_oid is None
    assert error == "Invalid or expired token"


def test_authenticate_with_email_returns_false_when_no_token(request_factory):
    req = request_factory()
    is_valid, user_oid, email, error = authenticate_with_email(req)
    assert is_valid is False
    assert user_oid is None
    assert email is None
    assert error is not None


def test_authenticate_with_email_delegates_to_auth_service(request_factory):
    req = request_factory(token="abc123")
    mock_service = MagicMock()
    mock_service.validate_token.return_value = (True, "oid-1", "user@example.com", None)

    is_valid, user_oid, email, error = authenticate_with_email(req, auth_service=mock_service)

    assert is_valid is True
    assert user_oid == "oid-1"
    assert email == "user@example.com"
    mock_service.validate_token.assert_called_once_with("abc123")


def test_authenticate_with_email_returns_generic_message_on_invalid_token(request_factory):
    req = request_factory(token="bad-token")
    mock_service = MagicMock()
    mock_service.validate_token.return_value = (False, None, None, "signature verification failed")

    is_valid, user_oid, email, error = authenticate_with_email(req, auth_service=mock_service)

    assert is_valid is False
    assert user_oid is None
    assert email is None
    assert error == "Invalid or expired token"
