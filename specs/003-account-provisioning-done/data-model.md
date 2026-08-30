# Data Model: Account Provisioning

**Date**: 2026-08-29

**Feature**: Account Provisioning (003-account-provisioning)

This document defines the single entity that implements account provisioning, and how it replaces the two entities `002-login-and-access-control` shipped with (see research.md §3 for why).

---

## Entity: Provisioned Account Entry

**Definition**: A record that both permits a Microsoft account to sign in and states which capability role(s) (Player, Administrator, or both) it holds. Matched by email for its first sign-in only; matched by a bound Microsoft object identifier (oid) thereafter.

**Scope**: Global; one entry per email.

### Properties

| Property | Type | Required | Value | Rationale |
|----------|------|----------|-------|-----------|
| `email` | string | Yes | Lowercased email address; also the document `id` and partition key | Sole identity of the entry; case-insensitive matching and display normalize to this value (FR-008) |
| `roles` | array of enum | Yes, min length 1 | Subset of `["Player", "Administrator"]` | At least one role is required to create/keep an entry (FR-003) |
| `objectId` | string (UUID) or null | No | Microsoft Entra object ID; `null` until the entry's first successful sign-in | Bound at first sign-in (FR-006); authoritative match for every later sign-in (FR-007) |
| `dateAdded` | ISO 8601 timestamp | Yes | When the entry was first created | Audit trail, mirrors 002's existing `dateAdded` field |
| `addedBy` | string | No | Administrator's email (or `"seed"` for the bootstrap entry) | Audit trail — who granted this access (constitution: additions must be auditable) |
| `dateBound` | ISO 8601 timestamp or null | No | When `objectId` was set | Distinguishes "never signed in" from "bound" without depending on `objectId`'s nullness alone in logs/telemetry |

No `dateRemoved`/`revokedBy`/soft-delete fields: removal (FR-012/FR-013, added 2026-08-30) is a hard delete of the Cosmos document, not a revocation state on a surviving entry — spec.md's Edge Cases treat a removed entry as gone entirely, matched the same as a never-provisioned email on any later sign-in attempt. Soft-delete/audit-revocation fields would model a state transition this feature doesn't have, so they remain dropped per Constitution Principle IV.

### Validation Rules

- `email` MUST be RFC 5322 well-formed (FR-005, via `pyisemail` — research.md §1) and MUST be stored/compared lowercased (FR-008).
- `roles` MUST contain at least one of `"Player"`/`"Administrator"`; a submission with none is rejected, not stored (FR-003).
- Adding an email that already has an entry MUST merge `roles` (union) and MUST NOT change `objectId`/`dateBound` (FR-009) — a resubmission with no new role is a no-op (spec.md Edge Cases).
- `objectId`, once non-null, is immutable through any code path this feature defines (no rebind/clear operation — spec.md Assumptions).

### State Transitions

```
Created (email + roles, objectId = null)
   │
   │  first successful sign-in with matching email
   ▼
Bound (objectId set, dateBound set)
   │
   │  every later sign-in: token.oid must equal objectId
   ▼
Bound (unchanged) ──── mismatched oid on sign-in ──→ access denied (entry unchanged)
```

`roles` can be widened (union) by an administrator at any point in either state, without affecting the `objectId`/`dateBound` transition above (FR-009).

---

## Storage Model (Cosmos DB Serverless)

**Container**: `provisionedAccountEntries` (replaces 002's `allowListEntries` and `capabilityAssignments`)

**Partition Key**: `/email` (research.md §4)

**Document Schema**:

```json
{
  "id": "player@example.com",
  "email": "player@example.com",
  "roles": ["Player"],
  "objectId": null,
  "dateAdded": "2026-08-29T20:00:00Z",
  "addedBy": "admin@example.com",
  "dateBound": null,
  "entityType": "ProvisionedAccountEntry"
}
```

After first sign-in:

```json
{
  "id": "player@example.com",
  "email": "player@example.com",
  "roles": ["Player"],
  "objectId": "550e8400-e29b-41d4-a716-446655440000",
  "dateAdded": "2026-08-29T20:00:00Z",
  "addedBy": "admin@example.com",
  "dateBound": "2026-08-29T20:05:00Z",
  "entityType": "ProvisionedAccountEntry"
}
```

**Validation Rules** (storage-level, mirroring the entity rules above):
- `id` and `email` MUST be identical and lowercased.
- `roles` MUST be non-empty and drawn only from `["Player", "Administrator"]`.
- No duplicate documents per email (the `id`/partition-key match enforces this at the Cosmos level: an add is an upsert keyed by `id`).

### Query Patterns and Performance

**Pattern 1: Sign-in lookup (email → entry), used by `login`/`me`**

```
Point read: container.read_item(id=email, partition_key=email)
```
**Cost**: ~1 RU (point read), same order as 002's existing oid-keyed point read.

**Pattern 2: Add or merge an entry (admin action)**

```
1. Point read by email (as above)
2. If absent: create with roles = [selected roles], objectId = null
3. If present: upsert with roles = union(existing.roles, selected roles); objectId/dateBound untouched
```
**Cost**: ~1 RU read + ~3-5 RU write.

**Pattern 3: List all entries (admin view)**

```
SELECT * FROM c WHERE c.entityType = "ProvisionedAccountEntry"
```
**Cost**: Cross-partition query, ~5-20 RU depending on result size — acceptable at this project's ~5-10 user scale, consistent with 002's own accepted cost for its equivalent admin list query.

---

## Migration Notes (from 002's Data Model)

| 002 concept | 002 storage | 003 replacement |
|---|---|---|
| Allow-List Entry (`allowListEntries`, keyed by `user_oid`) | Cosmos container | Folded into `provisionedAccountEntries` — its `email` field becomes the entry's identity; `user_oid` becomes `objectId` (nullable, bound not assumed) |
| Capability Assignment (`capabilityAssignments`, keyed by `user_oid` + capability) | Cosmos container | Folded into `provisionedAccountEntries.roles` (array on the same document, no separate per-role documents) |
| `dateRemoved`/`removedBy`/`dateRevoked`/`revokedBy` (soft-delete audit fields) | Both containers | Dropped — removal (FR-012/FR-013) is a hard delete, not a soft-revocation state, so these fields have no state to record (see Validation Rules above) |

No automated data migration script is defined here: per `007-azure-infrastructure-provisioning` and this project's current stage, there is no production data yet (Cosmos DB has not been provisioned/seeded outside of `src/backend/db/seed_data.py`'s manual test-data path), so the change ships as a schema replacement, not a live migration.
