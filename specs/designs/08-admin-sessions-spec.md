# Sessions (admin) — design spec

Reference implementation: `screens/08-admin-sessions.html`. Design system: **Modernist** (`screens/styles.css`).
App name: **LLM Dungeon**.

---

## 1. Purpose

The administrator's view of every play session in the instance: which story it belongs to, its
session identifier, how many tokens it has consumed, which account owns it, and a way to delete
it. Used for housekeeping and for spotting runaway token usage.

Administrators only.

---

## 2. Page structure

```
┌─────────────────────────────────────────────────────────────────────┐
│ NAV  LLM Dungeon ADMIN  Stories New story People Sessions │ Player  │  fixed
│                                       Refresh  Sign out  Ms Okafor  │
├─────────────────────────────────────────────────────────────────────┤
│ SESSIONS                                                            │
│ 14 sessions across 3 stories                                        │
│ ───────────────────────────────────────────────────                 │
│ ALL SESSIONS                                                        │
│ Story │ Session ID │ Total tokens │ Account │        [Delete]       │
│ …rows…                                                              │
│ Deleting a session removes the player's saved progress…             │
└─────────────────────────────────────────────────────────────────────┘
```

- Shell: `height: 100vh; overflow: hidden; display: flex; flex-direction: column`.
- Nav `flex: none`; content `flex: 1; overflow: auto; position: relative`.
- Content container: **full width**, `padding: 28px 16px 64px`. The 16px gutter matches the nav's
  `var(--space-4)`, so the heading and table share the nav brand's left edge. No `max-width`
  wrapper — the table needs the width.

This is the same shell as the People screen; the two admin list pages must be indistinguishable
in structure.

---

## 3. Navigation

Modernist `.nav`, background `var(--color-bg)`, `gap: 0`. Identical across all admin screens:

| Item | Notes |
| --- | --- |
| `LLM Dungeon` + `ADMIN` | `.nav-brand`; ADMIN suffix 13px, 400 weight, uppercase, `letter-spacing: 0.08em`, `var(--color-accent-700)` |
| Stories | |
| New story | |
| People | |
| Sessions | `aria-current="page"` on this screen |
| vertical rule | 1px `var(--color-divider)`, `margin: 0 16px` |
| Player view | exits to the player home |
| Refresh | `.btn .btn-ghost`, Lucide `refresh-cw` icon + label, `margin-left: auto` |
| Sign out | |
| Name chip | `.tag .tag-neutral` |

---

## 4. Page heading

- Kicker `SESSIONS` — 12px, uppercase, `letter-spacing: 0.1em`, `var(--color-accent-700)`.
- Heading — `<h2>`, computed: `{n} sessions across {m} stories`, singularised correctly
  (`1 session across 1 story`). Deleted stories are not counted in `m`.
- `.hr`, `margin: 20px 0 32px`.

No oversized display numeral on this page.

---

## 5. Sessions table

Label above: `ALL SESSIONS` — 11px, uppercase, `letter-spacing: 0.1em`,
`color-mix(in srgb, var(--color-text) 50%, transparent)`.

`.table`, `margin-top: 10px`. Columns, in order:

| Column | Treatment |
| --- | --- |
| **Story** | Story title in default ink. If the story has been deleted, render `(deleted story)` in `var(--color-neutral-700)`, italic — never an empty cell. |
| **Session ID** | Full UUID, monospace 13px (`ui-monospace, "SF Mono", Menlo, Consolas, monospace`), `.text-muted`, `overflow-wrap: anywhere` so it wraps instead of widening the table. |
| **Total tokens** | Right-aligned, `font-variant-numeric: tabular-nums`, `white-space: nowrap`, thousands separated (`16,393`). Header cell right-aligned too. Zero renders as `0`, not a dash. |
| **Account** | `.text-muted`, `overflow-wrap: anywhere`. |
| *(actions)* | `width: 1%`, `white-space: nowrap` — `.btn .btn-ghost` **Delete**, 12px, `padding: 6px 10px`, `gap: 6px`, with the Lucide `trash-2` icon before the label. |

Row order is the server's order (most recent first); the page does not sort or paginate.

Caption under the table: 13px muted, `max-width: 60ch` — "Deleting a session removes the
player's saved progress and its transcript. Token totals stay in the usage record."

---

## 6. Delete confirmation

`.dialog-backdrop` + `.dialog`, hidden by default (`display: none`; a `show` class sets
`display: grid`). Width `min(460px, 100%)`, `padding: 32px`.

- `.dialog-title` 24px — "Delete this session?"
- `.dialog-body` — names the session so the administrator can check it before committing:
  *Session `{first 8 chars}`… for `{account}` will be removed, along with its saved progress.
  This cannot be undone.*
- `.hr`, then `.btn-primary .btn-block` **Delete session** and `.btn-secondary .btn-block`
  **Keep it**.

Deletion never happens straight from the row. On confirm, the row is removed and the heading
count recomputes. Dismissing clears the pending selection.

---

## 7. Interaction

Shared button language from `styles.css` — do not re-declare it per page:

- Every button carries a visible 2px border at rest; transitions 0.12s.
- `.btn-ghost` (Refresh, Delete) — 2px divider border with `var(--color-neutral-700)` ink at
  rest; hover fills `var(--color-accent)` with `var(--color-bg)` text; pressed
  `var(--color-accent-600)`.
- `.btn-primary` — hover `var(--color-accent-600)` with a 3px accent halo; pressed
  `var(--color-accent-700)`.
- Nav links: transparent 2px bottom border, accent on hover and for `aria-current="page"`.
- Focus everywhere: `outline: 2px solid var(--color-accent); outline-offset: 2px`.

Delete is a ghost button, not a red one: destructive intent is carried by the dialog, not by a
permanently red control in every row.

---

## 8. States to support

| State | Rendering |
| --- | --- |
| Many sessions | As specified; the content area scrolls, the nav stays fixed. |
| One session | Heading singularises; table renders one row. |
| No sessions | Replace the table with a 15px paragraph on the same gutter: "No sessions yet. They appear here as soon as someone starts a story." Heading reads "No sessions". |
| Orphaned session | Story cell shows `(deleted story)`; the row is still deletable. |
| Zero tokens | `0` in the tokens column — a session that was created but never played. |

---

## 9. Design system rules that must hold

- Zero corner radius anywhere.
- All colour, type and spacing values come from `styles.css` custom properties.
- Button labels flush left inside wide/block buttons.
- Structural edges 2px; table row rules 1px (from `.table`).
- Accent red is reserved for the kicker, the primary dialog action, and hover/pressed states.
- Long identifiers and addresses wrap; the table never scrolls horizontally.

---

## 10. Data contract

```ts
type Session = {
  id: string;              // UUID, displayed in full
  storyTitle: string | null;   // null when the story has been deleted
  totalTokens: number;     // cumulative for the session
  account: string;         // owner's Microsoft account
};

type SessionsView = {
  currentAdmin: { name: string };
  sessions: Session[];     // most recent first
};
```

Counts in the heading are derived from `sessions`, not sent separately. Refresh re-reads the
list; there is no live polling.

---

## 11. Out of scope

Filtering and search, sorting by column, pagination, per-session transcript inspection, token
cost in currency, and date/time columns — none are specified yet. Responsive behaviour below
desktop width is also unspecified, as on the other admin screens.
