# Research: Account Listing

**Date**: 2026-09-05

All unknowns from this spec were resolved by the 2026-09-05 clarification session recorded in `spec.md`; no additional technical unknowns exist. This document records the two implementation-approach decisions those clarifications imply.

## 1. Where to sort the account list alphabetically by email

- **Decision**: Sort in `AccountProvisioningService.list_all()`, in Python, after fetching all rows from Cosmos DB (`sorted(entries, key=lambda e: e.email)`), rather than adding an `ORDER BY c.email` to the existing Cosmos SQL query.
- **Rationale**: The list is already bounded to ~5-10 rows (per `007-azure-infrastructure-provisioning`'s scale assumption, reaffirmed in this spec's Assumptions), so an in-memory sort costs nothing measurable and avoids touching the query string, its existing test coverage, or the container's indexing policy. `ProvisionedAccountEntry.email` is already normalized to lowercase at construction time (`__post_init__`), so a plain string sort is already a correct, stable, ASCII/locale-independent-enough ascending sort for this use case — no collation logic needed.
- **Alternatives considered**:
  - *Cosmos `ORDER BY c.email` in the query*: rejected — requires confirming/adding a composite/range index for `email` in the container's indexing policy, which is unnecessary complexity for a fixed small list (Principle IV) and would need its own emulator-backed index verification.
  - *Sort in the API handler (`list_accounts`) instead of the service*: rejected — `list_all` is the single source other callers (present or future) would also want sorted; sorting at the service boundary keeps the ordering guarantee co-located with the data access it depends on (lowercased `email`), matching where `add_or_merge` already does its own normalization.

## 2. How to express the "pending first sign-in" indicator

- **Decision**: Change the existing status-column text in `AccountList.jsx` from "Not yet signed in" to "Pending first sign-in" for any entry whose `bound` field (already returned by the existing `GET /api/manage/accounts` contract) is `false`. No new field, icon, or color is introduced.
- **Rationale**: The backend already computes and returns `bound` (`entry.objectId is not None`) in `_account_summary`; the frontend already branches on it. The clarification session settled that a "pending first sign-in" indicator is required and that it must be visually distinguished — the existing implementation already distinguishes it via a dedicated table cell showing plain text, which independently satisfies the constitution's "meaning is never carried by color alone" accessibility rule (UI Design System Requirements → Accessibility). The only gap is that the exact wording ("pending first sign-in") wasn't previously a stated, tested requirement — it was incidental copy. This is a minimal, in-place text change, not a new UI pattern, so it needs no new design-system component.
- **Alternatives considered**:
  - *Add a `tag`-styled badge (like the existing role tags) instead of plain text*: considered, but rejected for this feature — it would be a visual-design change to an existing screen contract (`specs/designs/05-admin-users.html`, which does not depict this indicator at all), which Principle XI requires an explicit design-agreement/sign-off step for before implementation. Kept the design surface area to a copy change so that sign-off step is narrow and fast; a future feature could restyle it if the user wants a badge instead, after design agreement.
