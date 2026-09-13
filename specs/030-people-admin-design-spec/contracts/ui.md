# UI Contract: People (Admin) Screen Design-Spec Conformance

## API change

**`GET /api/manage/accounts`** (`list_accounts`, `authorize_admin`-gated, unchanged path/verb):
each object in the `accounts` array gains one field.

```ts
type AccountSummary = {
  email: string;
  roles: ("Player" | "Administrator")[];
  bound: boolean;
  isSeedAdmin: boolean;
  dateAdded: string | null;   // NEW (FR-008) — ISO-8601, e.g. "2026-08-12T09:03:00Z"
};
```

`POST /api/manage/accounts` (`add_account`) already returns the same shape via
`_account_summary()`, so it gains `dateAdded` automatically — no separate change needed there.
`DELETE /api/manage/accounts` (`remove_account`) is unchanged (no account body returned).

## Component contract

All new page-scoped classes below live in `AdminAccounts.css` and are additive layout/state
modifiers; every control keeps its design-system class (`btn btn-primary`, `btn btn-secondary`,
`btn btn-ghost`, `table`, `tag tag-accent`, `tag tag-outline`, `dialog-backdrop`, `dialog`,
`input`, `field`), so hover, pressed, `:focus-visible`, and disabled stay the shared layer's
(research.md Decision 4).

### `AdminAccountsPage`

**Rendering contract**:
- Fixed shell / scrolling content split (`.people-shell`/`.people-scroll`), matching the same
  pattern `Home.css`'s `.home-shell`/`.home-colbody` already establishes: `.people-shell` is
  `height: 100vh; overflow: hidden; display: flex; flex-direction: column`; `.people-header`
  is `flex: none`; `.people-scroll` is `flex: 1; min-height: 0; overflow: auto`. No
  `max-width` wrapper anywhere (the design spec §2 is explicit that this is a deliberate
  departure from other admin pages, so the table gets its full width).
- Kicker `PEOPLE` above an `<h2>` reading `{n} accounts in LLM Dungeon`, where `n` is
  `accounts.length` — recomputed on every load/add/remove/refresh.
- `.hr` below the heading (inside `.people-header`, so it doesn't scroll away), then — inside
  `.people-scroll` — a two-column grid (`.people-grid`: `grid-template-columns:
  repeat(auto-fit, minmax(min(100%, 420px), 1fr)); gap: 40px; align-items: start`) containing
  the accounts table (left) and `AccountForm`'s panel (right, `max-width: 420px`).
- A muted caption below the table: "Removing an account revokes access at the next sign-in.
  Stories the player has finished stay in the class record." (static copy, not
  data-dependent).
- Loading/error states unchanged in behavior (`useRefreshable`'s existing `loading`/`error`
  flags), restyled to fit the new shell.

### `AccountList`

**Props**: unchanged (`accounts`, `token`, `currentUserEmail`, `onRemoved`).

**Rendering contract**:
- Table columns, in order: Microsoft account, Role, Status, Added, *(actions)*. (No Name
  column — research.md Decision 1.)
- Role cell: one `.tag` per role — `tag tag-outline` for `Player`, `tag tag-accent` for
  `Administrator` (research.md Decision 5), in a `flex; gap: 6px; flex-wrap: wrap` group.
- Status cell: `<span className="status status-on"><span className="dot" />Signed in</span>`
  when `account.bound`, else `<span className="status status-off"><span className="dot"
  />Never signed in</span>` (research.md Decision 2). The dot is square (no border-radius);
  the label text is always present — never color/dot alone.
- Added cell: `account.dateAdded` formatted short (e.g. `12 Aug`) via a small local formatter
  (mirrors `AdminPage.jsx`'s `formatLastPublished` pattern) — renders nothing (not a
  placeholder) when `dateAdded` is absent.
- Actions cell: unchanged eligibility logic (`isRemovable = !isSelf && !account.isSeedAdmin`);
  `.btn .btn-ghost` **Remove**, `padding: 6px 10px; font-size: 12px` per design spec §6; column
  `width: 1%; white-space: nowrap`.
- Remove-confirmation dialog: unchanged structure (`.dialog-backdrop`/`.dialog`, already
  conformant), copy unchanged ("Remove {email}?" / "They lose access... cannot be undone from
  here.").
- Long email values wrap (`overflow-wrap: anywhere`) rather than widening the table (FR-006).

### `AccountForm`

**Props**: unchanged (`token`, `onAdded`).

**Rendering contract**:
- Panel: `border: 1px solid var(--color-divider); background: var(--color-surface); padding:
  22px`.
- `.ovnum` `+` at 48px, `<h3>` "Add someone", muted 14px line ("They sign in with their school
  Microsoft account — no password is set here.").
- Form fields keep their existing `name`/behavior (`email`, `hasPlayer`, `hasAdministrator`)
  but gain the design's copy and layout: a labelled `.field` for the Microsoft account input
  (placeholder `ada.bell@school.internal`), a "Roles — choose one or both" field with two
  `min-height: 44px` checkbox rows each carrying a 15px label and a 13px muted description
  ("Sees only the stories assigned to their class." / "Creates and edits stories, adds and
  removes accounts."), and a muted note below them ("An account can hold both roles. You can
  grant the other role at any time.").
- `.hr`, then `.btn .btn-primary .btn-block` **Add account**, label flush left,
  `padding: 14px 16px`.
- Validation/error behavior unchanged (`role_required`/`invalid_email`/default messages from
  `MESSAGES`), restyled into the panel rather than a bare paragraph.

### Shared token layer (`designTokens.css`)

- Adds the canonical `styles.css`'s appended block: `.btn` transition, `.btn-secondary` 2px
  ink border + accent-fill hover/press, `.btn-primary` 2px accent border + halo hover +
  darker press, `.btn-ghost` 2px divider border with neutral-700 ink at rest + accent-fill
  hover/press, `.nav a` transparent-to-accent bottom border on hover/`aria-current="page"`
  (research.md Decision 4). Applies to every screen using these classes, not just People —
  including a resting-appearance change for `.btn-ghost` (ink color) and `.btn-secondary`
  (background). Every new hover/active rule is scoped `:not(:disabled):not([aria-disabled="true"])`
  so an inert control (e.g. `StatusPanel`'s hint button) keeps its disabled look on hover
  instead of lighting up like a live one.
