# Data Model: People (Admin) Screen Design-Spec Conformance

No new entity and no schema change. One existing field moves from "stored, not serialized" to
"stored and serialized" on one existing endpoint.

## Provisioned Account (existing — `ProvisionedAccountEntry`, `003-account-provisioning-done`)

| Field | Type | Already stored? | Already returned by `list_accounts`? | Change here |
| --- | --- | --- | --- | --- |
| `email` | string | yes | yes | none |
| `roles` | `("Player" \| "Administrator")[]` | yes | yes | none |
| `bound` (`objectId is not None`) | boolean | yes (as `objectId`) | yes (derived) | none |
| `isSeedAdmin` | boolean | derived from config | yes (derived) | none |
| `dateAdded` | ISO-8601 string | yes | **no** | **added (FR-008)** |
| `dateBound` | ISO-8601 string, first bind only | yes | no | not exposed — see *Scope note* Decision 2 (no honest "signed out X ago" can be computed from a first-bind-only timestamp) |

## Client-side view model (derived, not a new server entity)

The UI derives two presentation-only values per account — neither is a new stored field:

- **Status label**: `"Has signed in"` when `bound`, else `"Never signed in"` (spec.md FR-005;
  deliberately not the design's present-tense "Signed in" — paired with the accent dot that
  would read as live presence, which `bound` does not mean).
  Rendered as a `.status .status-on`/`.status-off` dot-plus-label pair, per
  `05-admin-users-spec.md` §6.1.
- **Added date**: `dateAdded` formatted client-side into the design's short form (e.g.
  `12 Aug`), the same pattern `AdminPage.jsx`'s `formatLastPublished` already uses for
  `lastPublishedAt`.

## Fields deliberately not modeled (Scope note)

- **Name** — no field exists or is added; the Microsoft account email remains the sole
  identity column (research.md Decision 1).
- **Live sign-in presence / last-seen** — no field exists or is added; only the binary
  bound/never-bound state is shown (research.md Decision 2).
