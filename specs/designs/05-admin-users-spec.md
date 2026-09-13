# People (admin) — design spec

Reference implementation: `screens/05-admin-users.html`. Design system: **Modernist** (`screens/styles.css`).
App name: **LLM Dungeon**.

---

## 1. Purpose

The administrator's account management screen. It lists every account in the instance, shows who
is currently signed in, lets an administrator add a new account, and lets them remove one with a
confirmation step.

Administrators only. Players never reach this screen.

---

## 2. Page structure

Full-viewport with a fixed nav and one scrolling content area:

```
┌────────────────────────────────────────────────────────────────┐
│ NAV  LLM Dungeon ADMIN  Stories New story People │ Player view │  fixed
│                                  Refresh  Sign out  Ms Okafor  │
├────────────────────────────────────────────────────────────────┤
│ PEOPLE                                                         │
│ 6 accounts in LLM Dungeon                                      │
│ ──────────────────────────────────────────────────             │
│ ALL ACCOUNTS                            ┌──────────────────┐   │
│ ┌────────────────────────────────────┐  │ +                │   │
│ │ Name │ Account │ Role │ Status │ … │  │ Add someone      │   │
│ │ …rows…                             │  │ [form]           │   │
│ └────────────────────────────────────┘  └──────────────────┘   │
│ Removing an account revokes access…                            │
└────────────────────────────────────────────────────────────────┘
```

- Shell: `height: 100vh; overflow: hidden; display: flex; flex-direction: column`.
- Nav: `flex: none`.
- Content: `flex: 1; overflow: auto; position: relative`.
- Content container: **full width**, `padding: 28px 16px 64px`. The 16px horizontal padding
  matches the nav's own `var(--space-4)` gutter, so the page heading, the table and the nav brand
  all sit on the same left edge. Do not re-introduce a `max-width` wrapper — the table needs the
  width.

---

## 3. Navigation

Modernist `.nav`, background `var(--color-bg)`, no gap between items.

| Item | Notes |
| --- | --- |
| `LLM Dungeon` + `ADMIN` | `.nav-brand`; the ADMIN suffix is 13px, 400 weight, uppercase, `letter-spacing: 0.08em`, `var(--color-accent-700)` |
| Stories | |
| New story | |
| People | `aria-current="page"` on this screen |
| vertical rule | 1px `var(--color-divider)`, `margin: 0 16px` |
| Player view | drops the admin out into the player experience |
| Refresh | `.btn .btn-ghost`, Lucide `refresh-cw` icon + label, `margin-left: auto` |
| Sign out | |
| Name chip | `.tag .tag-neutral`, the signed-in administrator's name |

---

## 4. Page heading

- Kicker `PEOPLE` — 12px, uppercase, `letter-spacing: 0.1em`, `var(--color-accent-700)`.
- Heading — `<h2>`, `{n} accounts in LLM Dungeon`. The count lives in the sentence; there is no
  oversized display numeral on this page.
- `.hr` below, `margin: 20px 0 32px`.

---

## 5. Body layout

`display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 420px), 1fr)); gap: 40px; align-items: start`.

Left cell: the accounts table. Right cell: the add-account panel, `max-width: 420px`.
Below ~880px the panel drops under the table automatically.

---

## 6. Accounts table

Label above the table: `ALL ACCOUNTS` — 11px, uppercase, `letter-spacing: 0.1em`,
`color-mix(in srgb, var(--color-text) 50%, transparent)`.

`.table`, `margin-top: 10px`. Columns:

| Column | Content |
| --- | --- |
| **Name** | Display name, default ink |
| **Microsoft account** | `.text-muted`, `overflow-wrap: anywhere` |
| **Role** | One or two `.tag`s in a `flex; gap: 6px; flex-wrap: wrap` group: `.tag-outline` **Player**, `.tag-accent` **Administrator**. An account can hold both. |
| **Status** | Sign-in status (§6.1) |
| **Added** | `.text-muted` short date, e.g. `12 Aug` |
| *(actions)* | `width: 1%`, `white-space: nowrap` — a `.btn .btn-ghost` **Remove**, 12px, `padding: 6px 10px` |

Caption under the table: 13px muted, `max-width: 60ch` — "Removing an account revokes access at
the next sign-in. Stories the player has finished stay in the class record."

### 6.1 Status column

A dot plus a short label, in one non-wrapping line:

```css
.status      { display: inline-flex; align-items: center; gap: 8px; white-space: nowrap; font-size: 13px; }
.status .dot { width: 8px; height: 8px; flex: none; }       /* square, no radius */
.status-on  .dot { background: var(--color-accent); }
.status-off .dot { background: var(--color-neutral-400); }
.status-off      { color: var(--color-neutral-700); }
```

| Value | Dot | Label |
| --- | --- | --- |
| Currently signed in | accent | `Signed in` |
| Signed out, has signed in before | neutral-400 | `Signed out · {relative time}` e.g. `Signed out · 2 days ago`, `Signed out · yesterday` |
| Invited but never used | neutral-400 | `Never signed in` |

The dot is a square — no border radius anywhere in this system. Never rely on the dot alone:
the text label always carries the meaning.

---

## 7. Add-account panel

`border: 1px solid var(--color-divider)`, `background: var(--color-surface)`, `padding: 22px`.

1. `.ovnum` `+` at 48px in `var(--color-accent)`.
2. `<h3>` "Add someone", 22px.
3. Muted 14px line — "They sign in with their school Microsoft account — no password is set here."
4. Form, `display: flex; flex-direction: column; gap: 18px`:
   - `.field` **Full name** → `.input`, placeholder `Ada Bell`.
   - `.field` **Microsoft account** → `.input`, placeholder `ada.bell@school.internal`.
   - `.field` **Roles — choose one or both**: two checkbox rows, each `min-height: 44px`,
     `display: flex; gap: 10px`, box `20×20` with `accent-color: var(--color-accent)`,
     a 15px label and a 13px muted description:
     - **Player** — "Sees only the stories assigned to their class." *(checked by default)*
     - **Administrator** — "Creates and edits stories, adds and removes accounts."
   - Muted 13px note — "An account can hold both roles. You can grant the other role at any time."
   - `.hr` at `height: 1px`.
   - `.btn .btn-primary .btn-block` **Add account**, `padding: 14px 16px`, label flush left.

No password field exists anywhere: authentication is Microsoft SSO.

---

## 8. Remove confirmation

`.dialog-backdrop` + `.dialog`, hidden by default (`display: none`; a `show` class sets
`display: grid`). Width `min(460px, 100%)`, `padding: 32px`.

- `.dialog-title` 24px — `Remove {name}?`
- `.dialog-body` — "They lose access to LLM Dungeon at their next sign-in. This cannot be undone
  from here."
- `.hr`, then `.btn-primary .btn-block` **Remove account** and `.btn-secondary .btn-block`
  **Keep it**.

Removal is never immediate from the table row; the dialog always intervenes.

---

## 9. Interaction

Button language is shared across every screen and lives in `styles.css` — do not re-declare it
per page:

- Every button carries a visible 2px border at rest and animates
  `background, color, border-color, box-shadow` over 0.12s.
- `.btn-secondary` — 2px ink border on the page ground; hover fills `var(--color-accent)` with
  `var(--color-bg)` text; pressed `var(--color-accent-600)`.
- `.btn-primary` — 2px accent border on the accent fill; hover `var(--color-accent-600)` with a
  3px accent halo; pressed `var(--color-accent-700)`, halo removed.
- `.btn-ghost` (Refresh, Remove) — 2px divider border with `var(--color-neutral-700)` ink at rest,
  so it still reads as a button; hover fills accent; pressed `var(--color-accent-600)`.
- Nav links carry a transparent 2px bottom border that turns accent on hover and for
  `aria-current="page"`.
- Focus everywhere: `outline: 2px solid var(--color-accent); outline-offset: 2px`.

Remove is a `.btn-ghost` rather than a red button: destructive intent is carried by the
confirmation dialog, not by a permanently red control.

---

## 10. Design system rules that must hold

- Zero corner radius anywhere, including the status dots.
- All colour, type and spacing values come from `styles.css` custom properties.
- Button labels flush left inside wide/block buttons.
- Structural edges are 2px rules; in-panel separators are 1px.
- Accent red is reserved for the kicker, the Administrator tag, the signed-in dot, the primary
  action, and hover/pressed states.
- Long email addresses wrap with `overflow-wrap: anywhere` rather than widening the table.

---

## 11. Data contract

```ts
type Account = {
  id: string;
  name: string;
  email: string;              // Microsoft account
  roles: ("player" | "administrator")[];   // one or both, never empty
  status:
    | { state: "signed-in" }
    | { state: "signed-out"; lastSeen: string }   // preformatted, e.g. "2 days ago"
    | { state: "never" };
  addedOn: string;            // preformatted short date, e.g. "12 Aug"
};

type PeopleView = {
  currentAdmin: { name: string };
  accounts: Account[];        // sorted newest-added first
};
```

Sign-in status is read at page load; the Refresh button re-reads it. There is no live polling.

---

## 12. Out of scope

Editing an existing account's roles inline, bulk import, class/group assignment, and audit
history — all specified elsewhere.
