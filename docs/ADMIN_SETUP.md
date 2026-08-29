# Administrator Setup: Account Provisioning

Account access is managed through the in-app Administration → Accounts
screen (`003-account-provisioning`), not by editing Cosmos DB directly.

## Bootstrapping the first administrator

A freshly deployed system has no provisioned accounts until one is seeded.
Set the `SEED_ADMIN_EMAIL` Function App setting (Terraform variable
`seed_admin_email`, see `infrastructure/terraform/variables.tf`) to the
Microsoft account email that should be the initial Administrator. On the
Function App's next cold start, a `ProvisionedAccountEntry` is created for
that email with the `Administrator` role (create-if-absent only — it never
overwrites an existing entry). Signing in with that account for the first
time binds it to that account's Microsoft object ID.

## Granting access to a new account

Signed in as an Administrator:

1. Open Administration → Accounts.
2. Enter the new account's email and select Player and/or Administrator.
3. Submit. The account can now sign in with that Microsoft account — its
   first sign-in binds its object ID to the entry.

Re-adding an email that's already provisioned merges the selected roles into
its existing entry (union, not a duplicate) and never touches its bound
object ID.

## Viewing provisioned accounts

The same Administration → Accounts screen lists every provisioned email,
its role(s), and whether it has signed in yet ("bound").

## Removing / revoking access

Not supported by this feature (explicit scope boundary — see
[`003-account-provisioning`'s spec](../specs/003-account-provisioning/spec.md)
Assumptions). Removing an entry today requires a direct edit to the
`provisionedAccountEntries` Cosmos DB container.

## Troubleshooting sign-in issues

Check Application Insights for structured logs from `auth_service` and
`account_provisioning_service` — each logs the `user_oid` involved in every
allow/deny decision (the oid is never included in the HTTP response itself,
only in server-side telemetry). A denial is generic (`access_denied`) for
both "no entry for this email" and "entry exists but its bound object ID
doesn't match" — by design, to avoid account enumeration.

## Example seed data

See `src/backend/db/seed_data.py` for a script that creates three example
provisioned accounts (Player, Admin, and a dual-role user) for local/test
environments.
