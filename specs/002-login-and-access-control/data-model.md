# Data Model: Login and Access Control

**Date**: 2026-08-28

**Feature**: Login and Access Control (002-login-and-access-control)

This document defines the entities, relationships, and state transitions that implement login and capability-based access control.

---

## Overview

The data model consists of two primary entities:

1. **Allow-List Entry** — determines whether a specific Microsoft account may sign in to the application
2. **Capability Assignment** — determines which menu items and application areas an allow-listed user can access

These entities work together with Azure AD (via tokens) to enforce both authentication (is this user known?) and authorization (what can this user do?).

---

## Entity 1: Allow-List Entry

**Definition**: A record that permits a specific Microsoft account to sign in to the application.

**Scope**: Global; applies to all users attempting to sign in.

### Properties

| Property | Type | Required | Value | Rationale |
|----------|------|----------|-------|-----------|
| User Object ID (oid) | UUID/GUID | Yes | Microsoft Entra ID's unique identifier for the user | Immutable, unique, assigned by Azure AD; used as primary key |
| Email Address | string | No | User's email (e.g., user@outlook.com or user@gmail.com) | Convenient for administration; not used for authentication |
| Date Added | timestamp | Yes | ISO 8601 datetime | Audit trail; helps identify stale entries |
| Date Removed | timestamp | No | ISO 8601 datetime (null if still active) | Soft-delete; allows reverting removals and maintains audit history |
| Added By | string | No | Administrator name or service account | Audit trail |
| Removed By | string | No | Administrator name or service account | Audit trail |
| Notes | text | No | Free-form notes (e.g., "Test account", "John's guest account") | Administrative reference only |

### Validation Rules

- **User Object ID must be present and valid**: Attempting to sign in with an account not in the allow-list results in access denial
- **Email address is optional but recommended**: Used only for UI/reporting; not for authentication or authorization
- **Soft-delete via date_removed**: Removing an entry sets `date_removed` to the current timestamp rather than deleting the row; allows audit history and reversal
- **Active entry = date_removed is NULL**: Backend checks `WHERE date_removed IS NULL` when validating sign-in

### State Transitions

An allow-list entry has no complex state machine:

1. **Created** (initial): Entry is added via administrator action
2. **Active** (normal operation): Entry is checked on every sign-in; user is allowed to proceed if entry exists and `date_removed` is NULL
3. **Disabled/Removed**: `date_removed` is set to the current timestamp; user is denied on next sign-in attempt
4. **Re-enabled** (recovery): `date_removed` is cleared (set to NULL); user can sign in again

---

## Entity 2: Capability Assignment

**Definition**: A record that assigns one or more capability roles (Player, Administrator) to an allow-listed user.

**Scope**: Per-user; determines which menu items and application areas each user can access.

### Properties

| Property | Type | Required | Value | Rationale |
|----------|------|----------|-------|-----------|
| User Object ID (oid) | UUID/GUID | Yes | Reference to Allow-List Entry's oid | Foreign key; identifies which user this capability applies to |
| Capability | enum | Yes | "Player" or "Administrator" | Type of capability granted |
| Date Assigned | timestamp | Yes | ISO 8601 datetime | Audit trail |
| Date Revoked | timestamp | No | ISO 8601 datetime (null if still active) | Soft-delete; allows reverting revocations |
| Assigned By | string | No | Administrator name or service account | Audit trail |
| Revoked By | string | No | Administrator name or service account | Audit trail |

### Validation Rules

- **User must exist in Allow-List Entry**: A capability can only be assigned to a user who has an active allow-list entry
- **Capability is one of the defined values**: Only "Player" or "Administrator" are valid; typos or custom values are rejected
- **A user may hold 0, 1, or 2 capabilities**: A single user can have both Player and Administrator roles simultaneously
- **Soft-delete via date_revoked**: Revoking a capability sets `date_revoked` to the current timestamp; the row is not deleted
- **Active capability = date_revoked is NULL**: Backend checks `WHERE date_revoked IS NULL` when fetching a user's capabilities

### State Transitions

A capability assignment has no complex state machine:

1. **Assigned** (initial): Capability is granted to a user via administrator action
2. **Active** (normal operation): Capability is checked on every API request and menu generation; user can access corresponding features
3. **Revoked**: `date_revoked` is set to the current timestamp; user loses access on next API request
4. **Re-enabled** (recovery): `date_revoked` is cleared; user regains access

---

## Entity 3: User Identity (Runtime, not persisted)

**Definition**: A user's authenticated identity and capabilities, constructed at request time from a valid token and the databases above.

**Scope**: Per-request; exists in memory only during request processing.

### Properties

| Property | Type | Source | Used For |
|----------|------|--------|----------|
| User Object ID (oid) | UUID/GUID | JWT token (validated) | Look up allow-list and capabilities |
| Email | string | JWT token (optional claim) | Display in UI; audit logs |
| Tenant ID | UUID/GUID | JWT token | Ensure token is for correct Azure AD tenant |
| Token Expiry | timestamp | JWT token | Session lifetime; triggers re-authentication |
| Is Allowed | boolean | Derived from Allow-List Entry | Determines if sign-in proceeds |
| Capabilities | set of strings | Derived from Capability Assignments | Determines menu items and endpoint access |
| Has Player | boolean | Derived from Capabilities | Menu logic: show game menu item? |
| Has Administrator | boolean | Derived from Capabilities | Menu logic: show admin menu item? |

### Lifecycle

1. **Unauthenticated state**: No token; user is not authenticated
2. **Token acquired**: Frontend obtains token from MSAL; includes it in `Authorization: Bearer` header
3. **Token validated**: Backend validates token signature, expiry, and issuer (Azure AD)
4. **Allow-list checked**: Backend queries Allow-List Entry; if not found or removed, request returns 403
5. **Capabilities fetched**: Backend queries Capability Assignments for all active roles
6. **Request processed**: API handler has full User Identity; can make authorization decisions based on capabilities
7. **Response sent**: Token included in response cookies or request headers as needed
8. **Token expires**: Browser requests new token via MSAL (automatic refresh); flow restarts at step 2

---

## Relationships

```
Allow-List Entry
  ├─ has_many ──> Capability Assignment (one-to-many)
  └─ has_one ──> User Identity (at request time, via oid match)

Capability Assignment
  ├─ belongs_to ──> Allow-List Entry (many-to-one, via oid)
  └─ belongs_to ──> User Identity (at request time, via oid)

User Identity (runtime construct)
  ├─ validates_against ──> Allow-List Entry
  └─ derives_capabilities_from ──> Capability Assignment

API Request
  ├─ includes ──> JWT Token
  ├─ triggers ──> User Identity Construction
  ├─ checks ──> Allow-List Entry
  ├─ checks ──> Capability Assignment
  └─ returns ──> 401 (no token) | 403 (not allowed or no capability) | 200 (success)
```

---

## Storage Model (Cosmos DB Serverless)

### Storage Architecture

This feature uses **Azure Cosmos DB in serverless mode** (on-demand pricing model) with JSON document storage. Two collections are defined below.

**Partition Key Strategy**: Both collections use `/user_oid` as the partition key. This approach:
- Optimizes queries for the primary access pattern (look up allow-list and capabilities by user oid)
- Provides natural partitioning if user base grows (each user's data is colocated)
- Simplifies data consistency (all per-user data in one logical partition)
- Serverless pricing means no wasted RU allocation

**Serverless Benefits**: No need to pre-provision throughput; Cosmos DB charges for consumed RUs. Small private app with occasional sign-ins will have minimal cost.

### Allow-List Entry Collection

**Collection Name**: `allowListEntries`

**Partition Key**: `/user_oid`

**Document Schema**:

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "user_oid": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@outlook.com",
  "dateAdded": "2026-08-28T20:00:00Z",
  "dateRemoved": null,
  "addedBy": "admin@outlook.com",
  "removedBy": null,
  "notes": "Test account for player functionality",
  "entityType": "AllowListEntry",
  "_ttl": -1
}
```

**Document Properties**:

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `id` | string (UUID) | Yes | Cosmos DB document ID; same as user_oid |
| `user_oid` | string (UUID) | Yes | Microsoft Entra ID object ID; matches partition key |
| `email` | string | No | User's email address (convenience; not used for queries) |
| `dateAdded` | ISO 8601 timestamp | Yes | When entry was created |
| `dateRemoved` | ISO 8601 timestamp or null | No | When entry was soft-deleted; null if active |
| `addedBy` | string | No | Administrator who added the entry |
| `removedBy` | string | No | Administrator who removed the entry |
| `notes` | string | No | Free-form notes (e.g., "Test account") |
| `entityType` | string | Yes | Constant: "AllowListEntry" (for type discrimination in queries) |
| `_ttl` | integer | No | Cosmos DB TTL in seconds; -1 means no expiry |

**Cosmos DB Indexes**:
- Automatic indexing on all properties
- Custom index path on `dateRemoved` (for filtering active entries)
- Custom index path on `email` (for administrative lookups)

**Validation Rules**:
- `id` and `user_oid` must be identical
- `user_oid` must be a valid UUID
- `dateRemoved` is null for active entries; timestamp for soft-deleted entries
- No duplicate entries (one entry per user_oid)

---

### Capability Assignment Collection

**Collection Name**: `capabilityAssignments`

**Partition Key**: `/user_oid`

**Document Schema**:

```json
{
  "id": "capability-550e8400-e29b-41d4-a716-446655440000-Player",
  "user_oid": "550e8400-e29b-41d4-a716-446655440000",
  "capability": "Player",
  "dateAssigned": "2026-08-28T20:00:00Z",
  "dateRevoked": null,
  "assignedBy": "admin@outlook.com",
  "revokedBy": null,
  "entityType": "CapabilityAssignment",
  "_ttl": -1
}
```

**Document Properties**:

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `id` | string | Yes | Composite: `capability-{user_oid}-{capability}` (e.g., "capability-550e...-Player") |
| `user_oid` | string (UUID) | Yes | Microsoft Entra ID object ID; matches partition key |
| `capability` | string | Yes | "Player" or "Administrator" |
| `dateAssigned` | ISO 8601 timestamp | Yes | When capability was granted |
| `dateRevoked` | ISO 8601 timestamp or null | No | When capability was soft-revoked; null if active |
| `assignedBy` | string | No | Administrator who assigned the capability |
| `revokedBy` | string | No | Administrator who revoked the capability |
| `entityType` | string | Yes | Constant: "CapabilityAssignment" (for type discrimination) |
| `_ttl` | integer | No | Cosmos DB TTL in seconds; -1 means no expiry |

**Cosmos DB Indexes**:
- Automatic indexing on all properties
- Custom index path on `dateRevoked` (for filtering active capabilities)
- Custom compound index on `(user_oid, capability, dateRevoked)` (for efficient active capability queries)

**Validation Rules**:
- `user_oid` must be a valid UUID
- `capability` must be exactly "Player" or "Administrator"
- `id` is composite: `capability-{user_oid}-{capability}`
- No duplicate entries (one entry per user_oid + capability combination)
- `dateRevoked` is null for active capabilities; timestamp for soft-revoked capabilities

---

### Query Patterns and Performance

**Pattern 1: Check if user is on allow-list**

```
SELECT * FROM c WHERE c.user_oid = @user_oid AND c.entityType = "AllowListEntry" AND c.dateRemoved = null
```

**Partition**: Scoped to single partition (user_oid) → High efficiency ✓
**RU Cost**: ~1-3 RU (point query)

**Pattern 2: Fetch user's active capabilities**

```
SELECT c.capability FROM c WHERE c.user_oid = @user_oid AND c.entityType = "CapabilityAssignment" AND c.dateRevoked = null
```

**Partition**: Scoped to single partition (user_oid) → High efficiency ✓
**RU Cost**: ~2-5 RU (partition range query)

**Pattern 3: Find user by email (admin lookup)**

```
SELECT * FROM c WHERE c.email = @email AND c.entityType = "AllowListEntry" AND c.dateRemoved = null
```

**Partition**: Cross-partition query → Moderate cost
**RU Cost**: ~3-10 RU (cross-partition; use sparingly for admin operations only)

**Pattern 4: List all active users (admin operation)**

```
SELECT * FROM c WHERE c.entityType = "AllowListEntry" AND c.dateRemoved = null
```

**Partition**: Cross-partition query → Higher cost
**RU Cost**: ~5-20 RU depending on result set size

---

### Migration Strategy

If migrating from SQL Server to Cosmos DB:

1. **Export data** from SQL tables (allow_list_entries, capability_assignments)
2. **Transform** to JSON documents with proper schema above
3. **Import** via Cosmos DB Data Migration Tool or bulk insert
4. **Verify** queries work as expected with new partition key strategy
5. **Switch** backend code to use Cosmos DB connection string

### Serverless RU Consumption

Expected consumption for small private app (10-100 users):

| Operation | Frequency/Day | RU/Operation | Total RU/Day |
|-----------|---------------|--------------|--------------|
| Sign-in (check allow-list + fetch capabilities) | 50 | 5 | 250 |
| Admin: Check user capabilities | 10 | 5 | 50 |
| Admin: Add/revoke capability | 5 | 3-5 | 25 |
| Total | — | — | ~325 RU/day |

**Serverless cost**: ~$0.30-0.50 USD/day (estimate based on Azure pricing; actual cost depends on region and pricing tier)

---

## API Contracts

### Authentication Flow

**Request** (from frontend):
```http
POST /api/auth/login
Authorization: Bearer <id_token>
```

**Response** (backend):
```http
200 OK
{
  "user_oid": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@outlook.com",
  "is_allowed": true,
  "capabilities": ["Player"],
  "has_player": true,
  "has_administrator": false
}
```

or

```http
403 Forbidden
{
  "error": "access_denied",
  "message": "Access not granted"
}
```

### Get Current User (/api/auth/me)

**Request** (from frontend):
```http
GET /api/auth/me
Authorization: Bearer <access_token>
```

**Response** (backend):
```http
200 OK
{
  "user_oid": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@outlook.com",
  "capabilities": ["Player", "Administrator"]
}
```

or

```http
401 Unauthorized
{
  "error": "unauthenticated"
}
```

or

```http
403 Forbidden
{
  "error": "access_denied",
  "message": "Access not granted"
}
```

---

## Design Decisions Rationale

**Why soft-delete (date_removed/date_revoked) instead of hard delete?**
- Allows reverting accidental removals without restoring from backup
- Maintains complete audit history
- Easy to implement and query

**Why store email as optional instead of required?**
- Allows add-by-oid if email is not known at registration time
- Supports accounts from non-standard domains without forcing email entry
- Simplifies initial setup

**Why separate Allow-List Entry from Capability Assignment?**
- Allows a user to be on the allow-list but have no capabilities (valid state per spec: shows "no access provisioned yet" message)
- Allows querying "how many users are on the allow-list?" vs "how many have Player capability?" separately
- Simplifies capability changes (revoke one capability without removing from allow-list)

**Why include audit fields (added_by, removed_by, date_added, date_removed)?**
- Required for compliance and troubleshooting
- Enables questions like "who removed this user?" or "when was this user added?"
- Minimal storage overhead for the value provided

---

## Summary

The data model is intentionally simple: two entities (Allow-List Entry and Capability Assignment) connected by user_oid, with soft-delete semantics for audit trails. This design supports:
- Multiple capability roles per user (Player, Administrator, both, or neither)
- Quick, efficient lookups for authentication and authorization
- Full audit history for compliance
- Recovery from accidental removals
- Independent management of allow-list and capabilities
