"""Shared fixtures for infrastructure tests (tests/infrastructure/).

These tests exercise the live, provisioned Azure infrastructure (see
specs/007-azure-infrastructure-provisioning) rather than mocks — they are
run post-`terraform apply`, either in CI (infrastructure-tests.yml) or
locally against an already-provisioned environment.
"""

import json
import subprocess
from pathlib import Path

import pytest
from azure.identity import DefaultAzureCredential

TERRAFORM_DIR = Path(__file__).resolve().parents[2] / "terraform"


@pytest.fixture(scope="session")
def azure_credential() -> DefaultAzureCredential:
    """Credential used by tests to call Azure APIs.

    Resolves via the standard DefaultAzureCredential chain: in GitHub Actions
    this picks up the federated OIDC token exchange configured by
    azure/login@v1 (no stored secrets); locally it falls back to the
    developer's `az login` session.
    """
    return DefaultAzureCredential()


@pytest.fixture(scope="session")
def terraform_outputs() -> dict:
    """Load `terraform output -json` from terraform/ as a dict of {name: value}.

    Requires that `terraform apply` has already run in TERRAFORM_DIR (state
    is read from the configured backend, not re-applied by this fixture).
    """
    result = subprocess.run(
        ["terraform", "output", "-json"],
        cwd=TERRAFORM_DIR,
        capture_output=True,
        text=True,
        check=True,
    )
    raw = json.loads(result.stdout)
    return {name: entry["value"] for name, entry in raw.items()}
