"""Verify the Static Web App has the Function App linked as its backend.

Without this link, Azure has no route for the frontend's relative /api/*
calls (authService.js, accountService.js) — the SWA's own router 404s
before the request ever reaches the Function App. Found live during
003-account-provisioning's quickstart validation (issue #32): sign-in
succeeded through MSAL, but GET /api/auth/me 404'd because neither a linked
backend nor Function App CORS had ever been provisioned.
"""

import pytest
from azure.mgmt.web import WebSiteManagementClient


@pytest.fixture(scope="session")
def subscription_id(terraform_outputs: dict) -> str:
    return terraform_outputs["resource_group_id"].split("/")[2]


@pytest.fixture(scope="session")
def web_client(azure_credential, subscription_id):
    return WebSiteManagementClient(azure_credential, subscription_id)


def test_static_web_app_has_function_app_linked_as_backend(web_client, terraform_outputs):
    resource_group_name = terraform_outputs["resource_group_name"]
    static_web_app_name = terraform_outputs["static_web_app_name"]
    expected_function_app_id = terraform_outputs["functions_app_id"]

    linked_backends = list(
        web_client.static_sites.get_linked_backends(resource_group_name, static_web_app_name)
    )

    assert linked_backends, (
        f"Static Web App {static_web_app_name!r} has no linked backend — "
        "relative /api/* calls from the frontend will 404 instead of reaching "
        "the Function App. Check azurerm_static_web_app_function_app_registration "
        "in main.tf."
    )
    backend_ids = {backend.backend_resource_id for backend in linked_backends}
    assert expected_function_app_id in backend_ids, (
        f"Static Web App {static_web_app_name!r} is linked to {backend_ids}, "
        f"expected the Function App {expected_function_app_id!r}"
    )
