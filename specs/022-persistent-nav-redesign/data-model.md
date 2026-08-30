# Phase 1 Data Model: Persistent Navigation & Design Refresh

No new persisted entity, API payload, or database schema is introduced by this
feature (Technical Context: Storage = N/A). The only "data" involved is derived,
in-memory UI state computed from data another feature already fetches.

## NavItem (derived, not persisted)

A `NavItem` is a rendering-time value, never stored or transmitted — `NavBar`
computes an array of these per render from `useCapabilities()`'s current values.

| Field | Type | Description |
|---|---|---|
| `label` | string | Visible link text (e.g. "Stories," "My stories," "People") |
| `href` | string | Route path the link navigates to |
| `visible` | boolean | Whether this item renders at all, derived from capability booleans |
| `isCurrent` | boolean | Whether this item's `href` matches `useLocation().pathname`; drives `aria-current="page"` and active styling |

**Derivation rules** (from spec FR-002/003/008, User Story 3):

- `hasAdministrator === true` → visible: "Stories," "New story," "People," "Player view"
- `hasPlayer === true` → visible: "My stories," "Badges"
- `hasAdministrator === true && hasPlayer === true` → both sets visible, plus the
  cross-role links ("Player view" on the admin side, "Admin" on the player side)
- `hasAdministrator === false && hasPlayer === false` → no primary destination links;
  only brand mark, sign-out, and user name (Edge Cases)
- "Sign out" and the user's display name are always visible, right-aligned,
  independent of capabilities (FR-004)

**State transitions**: None — `NavItem[]` is recomputed fresh on every render from
`useCapabilities()`'s current state and `useLocation()`'s current path; there is no
independent lifecycle to model.

## AuthenticatedLayout render mode (derived, not persisted)

A single derived enum, not stored:

| Value | When | Renders |
|---|---|---|
| `"nav"` | `useLocation().pathname` is any authenticated route except the story-play route | `NavBar` |
| `"title"` | `useLocation().pathname` matches the story-play route (`/game`) | `TitleBar` |

**Validation rule**: Exactly one of `NavBar`/`TitleBar` renders per authenticated
screen — never both, never neither (FR-001, FR-006, SC-002).

## Relationship to existing data

- `useCapabilities()` (`src/frontend/src/hooks/useCapabilities.js`) is the sole data
  source for `hasPlayer`/`hasAdministrator`; this feature adds no new field to its
  return shape and no new backend call.
- The signed-in user's display name shown in the nav bar's right-aligned tag is
  already available wherever `useCapabilities()`/`/api/auth/me` currently exposes it
  today (unchanged by this feature — see plan.md Principle X note).
- No entity in this feature has a lifecycle, persistence, or validation rule beyond
  the two derivation tables above — everything here is pure, render-time
  presentation logic over data that already exists.
