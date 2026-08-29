# Passed to: terraform init -backend-config=backend-prod.hcl
# Values here must match the Storage account created by infrastructure/scripts/bootstrap.sh
# (contracts/deployment-config-contract.md's Bootstrap Procedure, Step 1).

resource_group_name = "llm-dungeon"          # Pre-existing Resource Group, not created by Terraform
storage_account_name = "llmdungeontstateprod" # Created during bootstrap
container_name       = "terraform-state"
key                  = "production.tfstate"
