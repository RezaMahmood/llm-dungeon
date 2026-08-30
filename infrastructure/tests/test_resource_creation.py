"""Verify every resource `terraform apply` provisions exists with its expected
configuration (contracts/github-actions-contract.md's Infrastructure Testing
workflow). Run post-apply, either by infrastructure-tests.yml or locally.
"""

import pytest
from azure.mgmt.cognitiveservices import CognitiveServicesManagementClient
from azure.mgmt.cosmosdb import CosmosDBManagementClient
from azure.mgmt.storage import StorageManagementClient
from azure.mgmt.web import WebSiteManagementClient


@pytest.fixture(scope="session")
def subscription_id(terraform_outputs: dict) -> str:
    # resource_group_id looks like /subscriptions/<id>/resourceGroups/<name>
    return terraform_outputs["resource_group_id"].split("/")[2]


@pytest.fixture(scope="session")
def web_client(azure_credential, subscription_id):
    return WebSiteManagementClient(azure_credential, subscription_id)


@pytest.fixture(scope="session")
def storage_client(azure_credential, subscription_id):
    return StorageManagementClient(azure_credential, subscription_id)


@pytest.fixture(scope="session")
def cosmosdb_client(azure_credential, subscription_id):
    return CosmosDBManagementClient(azure_credential, subscription_id)


@pytest.fixture(scope="session")
def cognitive_client(azure_credential, subscription_id):
    return CognitiveServicesManagementClient(azure_credential, subscription_id)


def test_functions_app_exists(web_client, terraform_outputs):
    app = web_client.web_apps.get(
        terraform_outputs["resource_group_name"], terraform_outputs["functions_app_name"]
    )
    assert app is not None
    assert app.name == terraform_outputs["functions_app_name"]


def test_functions_managed_identity_enabled(web_client, terraform_outputs):
    app = web_client.web_apps.get(
        terraform_outputs["resource_group_name"], terraform_outputs["functions_app_name"]
    )
    assert app.identity is not None
    assert app.identity.type is not None and "SystemAssigned" in app.identity.type
    assert app.identity.principal_id == terraform_outputs["functions_managed_identity_principal_id"]


def test_functions_vnet_integration_present(web_client, terraform_outputs):
    app = web_client.web_apps.get(
        terraform_outputs["resource_group_name"], terraform_outputs["functions_app_name"]
    )
    assert app.virtual_network_subnet_id == terraform_outputs["functions_subnet_id"]


def test_storage_account_exists_and_public_access_disabled(storage_client, terraform_outputs):
    account = storage_client.storage_accounts.get_properties(
        terraform_outputs["resource_group_name"], terraform_outputs["storage_account_name"]
    )
    assert account is not None
    assert account.public_network_access == "Disabled"
    assert account.minimum_tls_version == "TLS1_2"


def test_cosmos_db_exists_and_public_access_disabled(cosmosdb_client, terraform_outputs):
    account = cosmosdb_client.database_accounts.get(
        terraform_outputs["resource_group_name"], terraform_outputs["cosmos_db_account_name"]
    )
    assert account is not None
    assert account.public_network_access == "Disabled"


def test_cosmos_database_and_container_exist(cosmosdb_client, terraform_outputs):
    database = cosmosdb_client.sql_resources.get_sql_database(
        terraform_outputs["resource_group_name"],
        terraform_outputs["cosmos_db_account_name"],
        terraform_outputs["cosmos_database_name"],
    )
    assert database is not None

    container = cosmosdb_client.sql_resources.get_sql_container(
        terraform_outputs["resource_group_name"],
        terraform_outputs["cosmos_db_account_name"],
        terraform_outputs["cosmos_database_name"],
        terraform_outputs["cosmos_container_name"],
    )
    assert container is not None


def test_azure_openai_account_exists_and_public_access_disabled(cognitive_client, terraform_outputs):
    account = cognitive_client.accounts.get(
        terraform_outputs["resource_group_name"], terraform_outputs["azure_openai_account_name"]
    )
    assert account is not None
    assert account.properties.public_network_access == "Disabled"


def test_azure_openai_model_deployment_exists(cognitive_client, terraform_outputs):
    deployment = cognitive_client.deployments.get(
        terraform_outputs["resource_group_name"],
        terraform_outputs["azure_openai_account_name"],
        terraform_outputs["azure_openai_deployment_name"],
    )
    assert deployment is not None

def test_gate_scenario_2_deliberate_failure(terraform_outputs):
    """Deliberate failure for 020-terraform-apply-gating Scenario 2 verification.

    Depends on terraform_outputs so it skips (like every other test in this
    file) when run outside a live-Azure context — e.g. the repo-wide test.yml
    job — and only fails for real inside infrastructure-tests.yml's job,
    where terraform init has already run against live state.
    """
    assert "gate_scenario_2_nonexistent_output" in terraform_outputs, (
        "intentional failure for gate verification — remove after Scenario 2"
    )
