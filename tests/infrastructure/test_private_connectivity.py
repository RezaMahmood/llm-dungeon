"""Verify Storage, Cosmos DB, and AI Foundry are reachable only over private
endpoints — never the public internet (FR-007, Principle VII).

Runs from wherever pytest executes (GitHub-hosted runners included, which sit
outside the VNet). What that vantage point CAN prove:
  - The private endpoint resources exist and their connections are Approved.
  - The public data-plane path is rejected (public_network_access disabled
    means requests to the public hostname fail, regardless of the caller's
    network location).
What it CANNOT prove from outside the VNet: that DNS resolves the same
hostnames to private IPs for an in-VNet caller — Azure Private DNS only
overrides resolution for clients using Azure-provided DNS within the linked
VNet, so that check stays a documented manual step (quickstart.md Scenario 4).
"""

import httpx
import pytest
from azure.mgmt.network import NetworkManagementClient


@pytest.fixture(scope="session")
def subscription_id(terraform_outputs: dict) -> str:
    return terraform_outputs["resource_group_id"].split("/")[2]


@pytest.fixture(scope="session")
def network_client(azure_credential, subscription_id):
    return NetworkManagementClient(azure_credential, subscription_id)


def _private_endpoint_name(resource_id: str) -> str:
    return resource_id.rstrip("/").split("/")[-1]


@pytest.mark.parametrize("output_key", ["storage", "cosmos", "openai"])
def test_private_endpoint_connection_approved(network_client, terraform_outputs, output_key):
    resource_group = terraform_outputs["resource_group_name"]
    prefix = terraform_outputs["functions_app_name"].rsplit("-func-", 1)[0]
    environment_suffix = terraform_outputs["functions_app_name"].rsplit("-func-", 1)[1]
    pe_name = f"{prefix}-pe-{output_key}-{environment_suffix}"

    endpoint = network_client.private_endpoints.get(resource_group, pe_name)
    assert endpoint is not None
    connections = endpoint.private_link_service_connections or endpoint.manual_private_link_service_connections
    assert connections, f"No connections found on private endpoint {pe_name}"
    assert connections[0].private_link_service_connection_state.status == "Approved"


@pytest.mark.parametrize(
    "output_key,hostname_output,path_and_query",
    [
        # A well-formed List Containers call — a bare GET to the account root
        # returns 400 (malformed request) regardless of network rules, so it
        # can't distinguish "blocked" from "reachable but rejected the shape".
        ("storage", "storage_blob_endpoint", "?comp=list"),
        # Cosmos DB's root path already performs a real account-level check.
        ("cosmos", "cosmos_endpoint", ""),
        # A real Cognitive Services REST call — the bare root path is a
        # shared, unauthenticated "service operational" health page that
        # responds regardless of this account's network access setting.
        ("openai", "azure_openai_endpoint", "openai/models?api-version=2023-05-15"),
    ],
)
def test_public_data_plane_access_denied(terraform_outputs, output_key, hostname_output, path_and_query):
    url = terraform_outputs[hostname_output].rstrip("/") + "/" + path_and_query
    try:
        response = httpx.get(url, timeout=10.0)
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout):
        return  # connection refused/timed out — public access is blocked, as expected
    assert response.status_code in (
        401,
        403,
    ), f"Expected public access to {output_key} to be denied, got {response.status_code}: {response.text[:200]}"
