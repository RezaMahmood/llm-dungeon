# UI Contract: Sessions (Admin) Screen — Design Conformance and Session Deletion

**Feature**: `031-sessions-admin-design-spec`

Acceptance reference: `specs/designs/08-admin-sessions.html` +
`specs/designs/08-admin-sessions-spec.md`. Where this file and the mockup disagree, the
disagreement is named below; everything unnamed follows the mockup.

---

## 1. Shell and navigation

Identical in structure to the People screen (`08-admin-sessions-spec.md` §2: the two admin
list pages "must be indistinguishable"). The shell, nav, and kicker rules come from
`AdminAccounts.css`'s established treatment rather than being re-derived.

- Shell fixed to the viewport; the content area is the only scroll container (constitution
  "Layout and scroll contract" #1, spec FR-001).
- Content container is full width with a 16px side gutter — **no `max-width` wrapper**; the
  table needs the width. This is the one structural difference from People.
- The Sessions nav item carries `aria-current="page"`.
- The header's Refresh control is the existing `RefreshButton`/`RefreshContext` plumbing
  (`019-spa-refresh-button`), published by the page exactly as `AdminAccountsPage` does
  (spec FR-016).

## 2. Heading

| Element | Content |
| --- | --- |
| Kicker | `SESSIONS` — 12px, uppercase, letter-spaced, accent-700 |
| Heading (`<h2>`) | `{n} sessions across {m} stories`, each half singularised independently; `No sessions` when the list is empty |

Counts derive from the rows (data-model.md → *Client projection*), recomputing after every
delete and refresh (spec FR-002). No oversized numeral on this screen.

## 3. Table

Label `ALL SESSIONS` above; `.table`; columns in this order:

| Column | Treatment | Requirement |
| --- | --- | --- |
| Story | Title in default ink; `(deleted story)` italic, neutral-700, when the story is gone | FR-004 |
| Session ID | Full UUID, monospace 13px, muted, `overflow-wrap: anywhere` | FR-003, FR-017 |
| Total tokens | Right-aligned, `tabular-nums`, `white-space: nowrap`, thousands-separated; `0` renders as `0` | FR-005 |
| Account | Muted, `overflow-wrap: anywhere` | FR-003, FR-017 |
| *(actions)* | `width: 1%`, nowrap; `.btn .btn-ghost` **Delete** with the Lucide `trash-2` icon before the label | FR-003 |

Row order is the server's order. The page does not sort, filter, or paginate. The table never
scrolls horizontally (FR-017).

**Caption beneath the table** — reworded from the mockup, the feature's one documented content
deviation (spec *Scope note: honest data*, SC-003):

> Deleting a session permanently removes the player's saved progress and its transcript. The
> tokens it spent stay counted in the usage telemetry.

The mockup's "Token totals stay in the usage record" is not used: it implies a per-session
ledger this application does not keep — a player session's total lives on the session document
and goes with it. What does survive is the per-call telemetry (Principle VI) and a story's own
cumulative total, and the wording above is true of both.

## 4. Empty state (FR-018)

Heading reads `No sessions`; the table is replaced by a 15px paragraph on the same gutter:

> No sessions yet. They appear here as soon as someone starts a story.

## 5. Delete confirmation (FR-007)

Renders the existing `components/Common/ConfirmDeleteDialog.jsx` (research.md Decision 6):

| Slot | Content |
| --- | --- |
| `title` | Delete this session? |
| `body` | Session `{first 8 chars of id}`… for `{account}` will be removed, along with its saved progress. This cannot be undone. |
| `confirmLabel` | Delete session |
| `cancelLabel` | Keep it |
| `workingLabel` | Deleting… |

**Documented deviation**: the shared dialog lays its two buttons out in a `.dialog-actions`
row; the mockup stacks two `.btn-block` buttons. The shared component wins — every other
destructive dialog in the product already reads this way, and reimplementing the dialog to
match one static file is exactly what the constitution's "MUST NOT reimplement a control the
system already provides" forbids.

**Behaviour**:

- Nothing is deleted from the row itself; the dialog is the only path to deletion.
- Dismissing (Keep it, or a backdrop click) clears the pending selection entirely.
  **Escape does not dismiss it** — the shared `ConfirmDeleteDialog` has never handled
  Escape, and neither does any other dialog in this product. Adding it here alone would
  make this one dialog behave unlike every other; adding it to the shared component is a
  product-wide change, out of scope for this feature. Recorded as a known gap, not
  implemented and not claimed.
- While the request is in flight both buttons are disabled and the confirm button shows
  `workingLabel`.
- On success: the row is removed, the heading recomputes, focus returns to a sensible place in
  the table.
- On failure: the dialog closes, the row stays, and an `role="alert"` notice says the session
  was not deleted (FR-014).
- On 404: the row is removed and the notice says it had already been removed (FR-015).

## 6. Player-facing side of a deletion

| Surface | Behaviour | Requirement |
| --- | --- | --- |
| Play surface, any action (turn, checkpoint, refresh, resume) | On `session_removed`, the page does **not** render an in-place notice — it leaves immediately | FR-012 |
| Route | `GamePage` navigates to `/menu` with one-shot router state | FR-012 |
| Home | A dismissible dialog (`.dialog`/`.dialog-backdrop`, `role="dialog"`, `aria-modal`) states the session has been removed; one acknowledging action, focused on open, closes it (as does a backdrop click — Escape, as above, does not) | FR-012, FR-013 |
| Home, after dismissal | Player stays on a current, working Home; the deleted session is absent from In progress | FR-011, FR-013 |
| Home, player not mid-session | The session is simply absent — no dialog, no placeholder, no error | FR-011 |

**Copy**: "This session has been removed. You can start this story again from your home page."
No actor is named (research.md Decision 4).

The router state is consumed on arrival and cleared, so a reload does not refire the dialog
(data-model.md → *Client state*).

## 7. Design-system rules that must hold

- Zero corner radius; all colour/type/spacing from `designTokens.css`; structural edges 2px,
  table row rules 1px.
- Accent red is reserved for the kicker, the dialog's primary action, and hover/pressed states.
  **Delete is a ghost button, not a red one** — destructive intent is carried by the dialog,
  not by a permanently red control in every row (`08-admin-sessions-spec.md` §7).
- All four interaction states come from the shared button language already in
  `designTokens.css` (030); this screen declares none of its own.
- Meaning never carried by colour alone: `(deleted story)` is a text label, not a tint.
- The Delete control is a real `<button>` with an accessible name that distinguishes rows (the
  icon alone is not the name), and the table is a real `<table>` with `<th scope="col">`.
</content>
