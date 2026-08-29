# Backend configuration is intentionally minimal here — the actual storage
# account/container/key values come from a -backend-config file (e.g.
# backend-prod.hcl) passed to `terraform init`, so the same configuration can
# target different environments' state without editing this file.
#
#   terraform init -backend-config=backend-prod.hcl
#
# The referenced storage account is created by the one-time bootstrap step
# (scripts/bootstrap.sh) before this backend can be initialized — see
# research.md §4 and contracts/deployment-config-contract.md.
terraform {
  backend "azurerm" {
    use_azuread_auth = true
  }
}
