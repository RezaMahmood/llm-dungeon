"""Verify GitHub Actions authenticates to Azure via federated OIDC only
(FR-011/FR-011a/FR-016/SC-004, spec.md US3 Acceptance Scenario 2) —
covering both the success path and the failure path.

Requires running inside a GitHub Actions job with `id-token: write`
permission (skipped elsewhere, e.g. local runs).
"""

import os

import pytest
import requests
from azure.core.exceptions import ClientAuthenticationError
from azure.identity import ClientAssertionCredential

GITHUB_ACTIONS_ONLY = pytest.mark.skipif(
    not os.environ.get("ACTIONS_ID_TOKEN_REQUEST_TOKEN"),
    reason="requires GitHub Actions OIDC context (ACTIONS_ID_TOKEN_REQUEST_TOKEN)",
)


def _fetch_github_oidc_token(audience: str = "api://AzureADTokenExchange") -> str:
    """Fetch a fresh GitHub Actions OIDC ID token for the given audience."""
    request_url = os.environ["ACTIONS_ID_TOKEN_REQUEST_URL"]
    request_token = os.environ["ACTIONS_ID_TOKEN_REQUEST_TOKEN"]
    response = requests.get(
        request_url,
        params={"audience": audience},
        headers={"Authorization": f"bearer {request_token}"},
        timeout=15,
    )
    response.raise_for_status()
    return response.json()["value"]


@GITHUB_ACTIONS_ONLY
def test_no_stored_azure_credentials_in_environment():
    """No long-lived credential material should exist alongside the OIDC federation."""
    forbidden_env_vars = [
        "AZURE_CLIENT_SECRET",
        "AZURE_CLIENT_CERTIFICATE_PATH",
        "AZURE_CLIENT_CERTIFICATE_PASSWORD",
        "AZURE_USERNAME",
        "AZURE_PASSWORD",
    ]
    present = [name for name in forbidden_env_vars if os.environ.get(name)]
    assert not present, f"Found stored-credential env vars, expected OIDC-only auth: {present}"


@GITHUB_ACTIONS_ONLY
def test_oidc_authentication_succeeds(azure_credential):
    """The real GitHub OIDC Managed Identity (via azure/login@v2's `az` session,
    picked up by DefaultAzureCredential's AzureCliCredential fallback) can
    acquire an Azure management token with zero stored secrets.
    """
    token = azure_credential.get_token("https://management.azure.com/.default")
    assert token is not None
    assert token.token


@GITHUB_ACTIONS_ONLY
def test_misconfigured_federated_credential_fails_clearly():
    """A federated credential pointed at a client ID Azure doesn't recognize
    must fail authentication explicitly — never fall back to a stored secret
    or silently proceed unauthenticated (FR-016 Edge Cases).
    """
    tenant_id = os.environ.get("AZURE_TENANT_ID")
    if not tenant_id:
        pytest.skip("AZURE_TENANT_ID not set in this job")

    nonexistent_client_id = "00000000-0000-0000-0000-000000000000"

    bad_credential = ClientAssertionCredential(
        tenant_id=tenant_id,
        client_id=nonexistent_client_id,
        func=_fetch_github_oidc_token,
    )

    with pytest.raises(ClientAuthenticationError):
        bad_credential.get_token("https://management.azure.com/.default")
