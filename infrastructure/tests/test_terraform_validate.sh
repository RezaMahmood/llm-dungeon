#!/usr/bin/env bash
# Wraps `terraform fmt -check` and `terraform validate` for CI and local use.
# Invoked by .github/workflows/terraform-validate.yml (T013).
#
# Uses `-backend=false` for init so this can run without the state Storage
# account existing yet (e.g. before bootstrap, or in a PR from a fork).

set -euo pipefail

TERRAFORM_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../terraform" && pwd)"

echo "== terraform fmt -check -recursive =="
terraform -chdir="$TERRAFORM_DIR" fmt -check -recursive

echo "== terraform init -backend=false =="
terraform -chdir="$TERRAFORM_DIR" init -backend=false -input=false

echo "== terraform validate -json =="
terraform -chdir="$TERRAFORM_DIR" validate -json

echo "✓ terraform fmt and validate passed"
