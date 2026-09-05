# Data Model: Account Listing

**Date**: 2026-09-05

This feature introduces **no new entity, field, or state transition**. It reads the `ProvisionedAccountEntry` entity defined and maintained by `003-account-provisioning-done` (`src/backend/models/provisioned_account_entry.py`) and adds an explicit, tested sort order over the collection when listing it.

## Provisioned Account Entry (existing — read-only here)

| Field | Type | Notes (relevant to this feature) |
|---|---|---|
| `email` | string | Normalized to lowercase at construction (`__post_init__`). This feature sorts the list ascending on this field. |
| `roles` | list[string] | Subset of `{"Player", "Administrator"}`. Displayed as-is; a role-merge (per `003`) already produces one entry with the union of roles, so the list never shows duplicate rows for one email. |
| `objectId` | string \| null | `null` until the account's first successful sign-in. This feature reads this field (via the API's derived `bound` boolean, see below) to decide whether to show the "pending first sign-in" indicator — `objectId is None` → pending. |
| `dateAdded`, `addedBy`, `dateBound`, `id`, `entityType` | — | Unused by this feature; unchanged. |

No migration, index change, or new container is required.

## Derived/API-level shape (existing — unchanged by this feature except ordering)

`_account_summary()` in `src/backend/api/admin/accounts.py` already derives, per entry:

```json
{ "email": "...", "roles": ["..."], "bound": true, "isSeedAdmin": false }
```

- `bound`: `true` iff `objectId is not None`. This feature's "pending first sign-in" indicator is the frontend's rendering of `bound === false` — no new field is added to this shape.
- `isSeedAdmin`: unrelated to this feature (used for remove-button gating, not listing).

## Ordering (new in this feature)

`AccountProvisioningService.list_all()` returns entries sorted ascending by `email` (already-lowercased string sort). This ordering is a service-layer guarantee, not a new persisted field — it is computed at read time on every call.
