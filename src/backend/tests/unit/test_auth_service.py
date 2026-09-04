"""Unit tests for AuthService.validate_token."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import jwt
import pytest

from backend.services.auth_service import AuthService

TENANT_ID = "test-tenant-id"
APP_ID = "test-app-id"
ISSUER = f"https://login.microsoftonline.com/{TENANT_ID}/v2.0"


def _rsa_key_pair():
    from cryptography.hazmat.primitives.asymmetric import rsa

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key, private_key.public_key()


@pytest.fixture(scope="module")
def key_pair():
    return _rsa_key_pair()


def _make_token(private_key, *, issuer=ISSUER, audience=APP_ID, oid="user-oid-123", email="user@example.com", exp_delta=3600):
    payload = {
        "oid": oid,
        "iss": issuer,
        "aud": audience,
        "exp": int(time.time()) + exp_delta,
        "iat": int(time.time()),
    }
    if email is not None:
        payload["email"] = email
    return jwt.encode(payload, private_key, algorithm="RS256")


def _service_with_mocked_key(public_key):
    service = AuthService(jwks_uri="https://example.invalid/keys", issuer=ISSUER, audience=APP_ID)
    signing_key = MagicMock()
    signing_key.key = public_key
    mock_jwk_client = MagicMock()
    mock_jwk_client.get_signing_key_from_jwt.return_value = signing_key
    service._jwk_client = mock_jwk_client
    service._jwk_client_created_at = time.time()
    return service


def test_validate_token_with_valid_token_returns_true_oid_and_email(key_pair):
    private_key, public_key = key_pair
    service = _service_with_mocked_key(public_key)
    token = _make_token(private_key)

    is_valid, user_oid, email, error = service.validate_token(token)

    assert is_valid is True
    assert user_oid == "user-oid-123"
    assert email == "user@example.com"
    assert error is None


def test_validate_token_lowercases_are_not_applied_here_email_passed_through_raw(key_pair):
    # Lowercasing is the caller's responsibility (FR-008); validate_token passes the
    # claim through unchanged.
    private_key, public_key = key_pair
    service = _service_with_mocked_key(public_key)
    token = _make_token(private_key, email="Mixed.Case@Example.com")

    _is_valid, _user_oid, email, _error = service.validate_token(token)

    assert email == "Mixed.Case@Example.com"


def test_validate_token_with_expired_token_returns_false(key_pair):
    private_key, public_key = key_pair
    service = _service_with_mocked_key(public_key)
    token = _make_token(private_key, exp_delta=-3600)

    is_valid, user_oid, email, error = service.validate_token(token)

    assert is_valid is False
    assert user_oid is None
    assert email is None


def test_validate_token_with_invalid_signature_returns_false(key_pair):
    _private_key, public_key = key_pair
    other_private_key, _other_public_key = _rsa_key_pair()
    service = _service_with_mocked_key(public_key)
    token = _make_token(other_private_key)

    is_valid, user_oid, email, error = service.validate_token(token)

    assert is_valid is False
    assert user_oid is None
    assert email is None


def test_validate_token_with_wrong_issuer_returns_false(key_pair):
    private_key, public_key = key_pair
    service = _service_with_mocked_key(public_key)
    token = _make_token(private_key, issuer="https://login.microsoftonline.com/wrong-tenant/v2.0")

    is_valid, user_oid, email, error = service.validate_token(token)

    assert is_valid is False
    assert user_oid is None
    assert email is None


def test_validate_token_accepts_personal_microsoft_account_issuer(key_pair):
    """A personal Microsoft account (e.g. the seed administrator's own
    @hotmail.com address — spec.md requires "it must be a microsoft
    account", not restricted to this org's tenant) presents an issuer for
    Microsoft's fixed MSA "consumers" tenant, not AZURE_TENANT_ID. Found live:
    every sign-in from such an account was rejected before this was accepted
    as a valid issuer alongside the org tenant.
    """
    private_key, public_key = key_pair
    consumers_issuer = "https://login.microsoftonline.com/9188040d-6c67-4c5b-b112-36a304b66dad/v2.0"
    service = AuthService(
        jwks_uri="https://example.invalid/keys",
        issuer=(ISSUER, consumers_issuer),
        audience=APP_ID,
    )
    signing_key = MagicMock()
    signing_key.key = public_key
    mock_jwk_client = MagicMock()
    mock_jwk_client.get_signing_key_from_jwt.return_value = signing_key
    service._jwk_client = mock_jwk_client
    service._jwk_client_created_at = time.time()
    token = _make_token(private_key, issuer=consumers_issuer)

    is_valid, user_oid, email, error = service.validate_token(token)

    assert is_valid is True
    assert user_oid == "user-oid-123"
    assert email == "user@example.com"


def test_validate_token_accepts_app_id_uri_audience(key_pair):
    """Entra ID may stamp the access token's `aud` as the App ID URI
    (`api://{clientId}`) rather than the bare client ID GUID, depending on the
    app registration's accessTokenAcceptedVersion setting (#212: every login
    was hitting 401 from /api/auth/me because only the bare GUID was
    accepted).
    """
    private_key, public_key = key_pair
    app_id_uri = f"api://{APP_ID}"
    service = AuthService(
        jwks_uri="https://example.invalid/keys",
        issuer=ISSUER,
        audience=(APP_ID, app_id_uri),
    )
    signing_key = MagicMock()
    signing_key.key = public_key
    mock_jwk_client = MagicMock()
    mock_jwk_client.get_signing_key_from_jwt.return_value = signing_key
    service._jwk_client = mock_jwk_client
    service._jwk_client_created_at = time.time()
    token = _make_token(private_key, audience=app_id_uri)

    is_valid, user_oid, email, error = service.validate_token(token)

    assert is_valid is True
    assert user_oid == "user-oid-123"
    assert email == "user@example.com"


def test_default_valid_audiences_include_bare_id_and_app_id_uri():
    with patch("backend.services.auth_service.config") as mock_config:
        mock_config.jwks_uri.return_value = "https://example.invalid/keys"
        mock_config.valid_issuers.return_value = (ISSUER,)
        mock_config.valid_audiences.return_value = (APP_ID, f"api://{APP_ID}")
        service = AuthService()

    assert service._valid_audiences == (APP_ID, f"api://{APP_ID}")


def test_default_valid_issuers_include_both_org_and_consumers_tenants():
    with patch("backend.services.auth_service.config") as mock_config:
        mock_config.jwks_uri.return_value = "https://example.invalid/keys"
        mock_config.AZURE_APP_ID = APP_ID
        mock_config.valid_issuers.return_value = (
            ISSUER,
            "https://login.microsoftonline.com/9188040d-6c67-4c5b-b112-36a304b66dad/v2.0",
        )
        service = AuthService()

    assert service._valid_issuers == (
        ISSUER,
        "https://login.microsoftonline.com/9188040d-6c67-4c5b-b112-36a304b66dad/v2.0",
    )


def test_validate_token_with_no_token_returns_false():
    service = AuthService(jwks_uri="https://example.invalid/keys", issuer=ISSUER, audience=APP_ID)

    is_valid, user_oid, email, error = service.validate_token("")

    assert is_valid is False
    assert user_oid is None
    assert email is None
    assert error is not None


def test_validate_token_missing_email_claim_returns_none_email(key_pair):
    private_key, public_key = key_pair
    service = _service_with_mocked_key(public_key)
    token = _make_token(private_key, email=None)

    is_valid, user_oid, email, error = service.validate_token(token)

    assert is_valid is True
    assert user_oid == "user-oid-123"
    assert email is None
