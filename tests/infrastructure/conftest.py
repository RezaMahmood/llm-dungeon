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

TERRAFORM_DIR = Path(__file__).resolve().parents[2] / "infrastructure" / "terraform"


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
    """Load `terraform output -json` from infrastructure/terraform/ as a dict of {name: value}.

    Requires that `terraform apply` has already run in TERRAFORM_DIR (state
    is read from the configured backend, not re-applied by this fixture) and
    that this job has already run `terraform init -backend-config=...` with
    Azure credentials able to read the state (infrastructure-tests.yml does
    both). Skips cleanly — rather than erroring — when run outside that
    context, e.g. the generic test.yml job, which has neither.
    """
    try:
        result = subprocess.run(
            ["terraform", "output", "-json"],
            cwd=TERRAFORM_DIR,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        pytest.skip(f"terraform not runnable in this context: {exc}")

    if result.returncode != 0:
        pytest.skip(f"terraform output failed (not initialized against live state here): {result.stderr[:300]}")

    raw = json.loads(result.stdout)
    return {name: entry["value"] for name, entry in raw.items()}
