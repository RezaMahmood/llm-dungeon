"""Verify the deployed Function App's Entra ID app settings actually match
the tenant and app registration configured for this project (FR-013/FR-014,
SC-006) — added after /speckit-analyze found that AZURE_APP_ID silently fell
back to the wrong client ID when TF_VAR_azure_app_id wasn't wired through
terraform-apply.yml (see plan.md's 2026-08-29 Amendment).

Requires AZURE_TENANT_ID / AZURE_APP_ID in the environment (set by
infrastructure-tests.yml from the matching GitHub repository variables).
Skipped cleanly when run outside that context, e.g. locally without them set.
"""

import os

import pytest
from azure.mgmt.web import WebSiteManagementClient


@pytest.fixture(scope="session")
def subscription_id(terraform_outputs: dict) -> str:
    return terraform_outputs["resource_group_id"].split("/")[2]


@pytest.fixture(scope="session")
def web_client(azure_credential, subscription_id):
    return WebSiteManagementClient(azure_credential, subscription_id)


@pytest.fixture(scope="session")
def function_app_settings(web_client, terraform_outputs) -> dict:
    settings = web_client.web_apps.list_application_settings(
        terraform_outputs["resource_group_name"], terraform_outputs["functions_app_name"]
    )
    return settings.properties or {}


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        pytest.skip(f"{name} not set in this job")
    return value


def test_function_app_tenant_id_matches_configured_tenant(function_app_settings):
    expected = _require_env("AZURE_TENANT_ID")
    assert function_app_settings.get("AZURE_TENANT_ID") == expected


def test_function_app_app_id_matches_login_app_registration(function_app_settings):
    """Guards against main.tf's `var.azure_app_id != "" ? ... : var.azure_client_id`
    fallback silently writing the GitHub OIDC deploy identity's client ID
    instead of the actual MSAL app registration when TF_VAR_azure_app_id is
    unset or empty.
    """
    expected = _require_env("AZURE_APP_ID")
    deploy_client_id = os.environ.get("AZURE_CLIENT_ID")
    actual = function_app_settings.get("AZURE_APP_ID")

    assert actual == expected, (
        f"AZURE_APP_ID app setting is {actual!r}, expected the login app "
        f"registration's client ID {expected!r} — check that "
        "TF_VAR_azure_app_id is wired into terraform-apply.yml"
    )
    if deploy_client_id:
        assert actual != deploy_client_id, (
            "AZURE_APP_ID app setting matches the GitHub OIDC deploy identity's "
            "client ID, not a dedicated login app registration — this is the "
            "exact fallback bug FR-013/FR-014 guard against"
        )
