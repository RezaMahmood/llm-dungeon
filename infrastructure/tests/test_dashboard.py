"""Verify the Azure Portal Dashboard provisioned by `terraform apply` exists
(plan.md's Constitution Check, Principle I). Run post-apply, either by
infrastructure-tests.yml or locally.

Panel-level data correctness is deliberately not covered here - see
quickstart.md's manual validation steps and research.md §7.
"""

import pytest
from azure.mgmt.resource.resources import ResourceManagementClient


@pytest.fixture(scope="session")
def subscription_id(terraform_outputs: dict) -> str:
    # resource_group_id looks like /subscriptions/<id>/resourceGroups/<name>
    return terraform_outputs["resource_group_id"].split("/")[2]


@pytest.fixture(scope="session")
def resource_client(azure_credential, subscription_id):
    return ResourceManagementClient(azure_credential, subscription_id)


def test_dashboard_exists(resource_client, terraform_outputs):
    # No dedicated dashboard-specific SDK client exists for
    # Microsoft.Portal/dashboards, so this looks it up as a generic resource
    # by its Terraform-exported resource ID.
    dashboard = resource_client.resources.get_by_id(
        terraform_outputs["dashboard_id"],
        api_version="2020-09-01-preview",
    )
    assert dashboard is not None
    assert dashboard.name == terraform_outputs["dashboard_name"]
