# Contract: FR-005 Automated Checks per Keyless-Auth Outcome

This spec exposes no library API, CLI, or HTTP endpoint — its only "external interface" is
the set of automated checks FR-005 requires (one per keyless-authentication outcome) and
the CI workflow that runs them. This contract documents that interface: what each check
asserts, and what a passing/failing result means.

## Outcome → Check mapping

| Outcome (spec.md FR-005) | Test | Assertion | Pre-conditions |
|---|---|---|---|
| Successful OIDC-authenticated GitHub Actions run | `test_oidc_authentication.py::test_oidc_authentication_succeeds` | `DefaultAzureCredential`-equivalent acquires a valid `https://management.azure.com/.default` token via the GitHub OIDC Managed Identity, with no stored credential env vars present | Running inside a real GitHub Actions job with `id-token: write` (`ACTIONS_ID_TOKEN_REQUEST_TOKEN` set); skipped otherwise |
| Failed/missing OIDC authentication | `test_oidc_authentication.py::test_misconfigured_federated_credential_fails_clearly` | A `ClientAssertionCredential` pointed at a nonexistent client ID raises `ClientAuthenticationError` — never falls back or succeeds silently | Same as above; requires `AZURE_TENANT_ID` |
| No stored Azure credentials alongside OIDC federation | `test_oidc_authentication.py::test_no_stored_azure_credentials_in_environment` | None of `AZURE_CLIENT_SECRET`, `AZURE_CLIENT_CERTIFICATE_PATH`, `AZURE_CLIENT_CERTIFICATE_PASSWORD`, `AZURE_USERNAME`, `AZURE_PASSWORD` are set | Same as above |
| Private-endpoint-authenticated calls to Storage/Cosmos DB/AI Foundry | `test_private_connectivity.py::test_private_endpoint_connection_approved` (parametrized: `storage`, `cosmos`, `openai`) | The named private endpoint exists and its connection state is `Approved` | `terraform_outputs` fixture (reads live `terraform output` from the deployed `production` state); Azure credential with read access to the Resource Group |
| Rejected public-network connection attempts to Storage/Cosmos DB/AI Foundry | `test_private_connectivity.py::test_public_data_plane_access_denied` (parametrized: `storage`, `cosmos`, `openai`) | A direct HTTPS call to the resource's public hostname either fails to connect/times out, or returns `401`/`403` | Same as above; resource must have `public_network_access_enabled = false` |

## Execution contract

- **Runner**: `.github/workflows/infrastructure-tests.yml`, on a nightly cron (`0 2 * * *`
  UTC) and `workflow_dispatch`. Not run on every PR (research.md R6) — these checks require
  a live federated-OIDC context and already-deployed infra that a PR job doesn't have.
- **Auth for the check runner itself**: `azure/login@v2` using the same GitHub OIDC
  Managed Identity this spec's FR-003 governs (`vars.AZURE_CLIENT_ID` /
  `vars.AZURE_TENANT_ID` / `vars.AZURE_SUBSCRIPTION_ID`) — i.e., the test suite's own ability
  to run is itself a live instance of the FR-003 success path.
- **Failure handling**: A failing check in this suite fails the workflow run (standard
  pytest exit code), surfaced in the Actions run summary; there is no separate alerting
  configured beyond GitHub's own workflow-failure notifications (out of scope for this spec
  to add).
- **Inputs**: `infrastructure/tests/conftest.py`'s `terraform_outputs` fixture (shells out to
  `terraform output -json` against the already-initialized `production` backend) and
  `azure_credential` fixture (Azure CLI-backed credential from the `azure/login@v2` session).
- **Idempotency**: All checks are read-only against live Azure state (`GET`/token-acquisition
  calls only) — safe to re-run at any cadence without side effects.
