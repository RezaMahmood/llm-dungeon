# Administrator Setup: Allow-List and Capabilities

This feature has no admin UI yet for managing the allow-list and capabilities
(a future feature may add one). Until then, administrators manage these
directly in Cosmos DB.

## Adding a user to the allow-list

Insert a document into the `allowListEntries` container (partition key
`/user_oid`):

```json
{
  "id": "<user-oid>",
  "user_oid": "<user-oid>",
  "email": "user@example.com",
  "dateAdded": "2026-08-29T00:00:00Z",
  "dateRemoved": null,
  "addedBy": "admin@example.com",
  "notes": "",
  "entityType": "AllowListEntry"
}
```

`user_oid` is the user's Microsoft Entra ID object ID (the `oid` claim in
their token) — find it via the Azure AD portal's Users blade, or ask the
user to sign in once and check the denial log (Application Insights) for
their oid.

## Assigning a capability

Insert a document into the `capabilityAssignments` container (partition key
`/user_oid`):

```json
{
  "id": "capability-<user-oid>-Player",
  "user_oid": "<user-oid>",
  "capability": "Player",
  "dateAssigned": "2026-08-29T00:00:00Z",
  "dateRevoked": null,
  "assignedBy": "admin@example.com",
  "entityType": "CapabilityAssignment"
}
```

`capability` must be exactly `"Player"` or `"Administrator"`. A user can have
both — insert one document per capability.

## Removing / revoking access

Soft-delete rather than hard-delete, to preserve the audit trail:

- **Remove from allow-list**: set `dateRemoved` to the current timestamp on
  the `allowListEntries` document.
- **Revoke a capability**: set `dateRevoked` to the current timestamp on the
  relevant `capabilityAssignments` document.

Changes take effect on the user's next API request (no re-login required to
be denied; a menu refresh or page navigation to see the updated menu).

## Troubleshooting sign-in issues

Check Application Insights for structured logs from `auth_service`,
`allow_list_service`, and `capability_service` — each logs the `user_oid`
involved in every allow/deny decision (the oid is never included in the
HTTP response itself, only in server-side telemetry).

## Example seed data

See `src/backend/db/seed_data.py` for a script that creates three example users
(Player, Admin, and a dual-role user) for local/test environments.
