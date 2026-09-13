# Quickstart: People (Admin) Screen Design-Spec Conformance

## Prerequisites

- Backend and frontend dev servers running per the repo's normal local setup (Cosmos DB
  emulator, Azure Functions host, Vite dev server).
- Signed in as an account holding the Administrator role (the seed administrator works).

## Validate the restyled screen

1. Sign in and navigate to **People** (`/admin/accounts`) from the admin nav.
2. Confirm the page has no page-level scrollbar of its own beyond the content area, shows a
   `PEOPLE` kicker and a heading reading `{n} accounts in LLM Dungeon`, and lays the accounts
   table and the "Add someone" panel out side by side (two-column) at desktop width.
3. Resize the browser narrower than ~880px and confirm the add-account panel moves below the
   table rather than being clipped.

## Validate the accounts table

4. Confirm each row shows: Microsoft account (email), one or two role tags (`Player` outlined,
   `Administrator` accent-filled), a Status cell reading either "Has signed in" (accent dot) or
   "Never signed in" (neutral dot) — never a third "Signed out" state — and an Added date.
5. Confirm a Remove action appears for every row except the signed-in administrator's own row
   and the seed administrator's row.

## Validate add/remove behavior is unchanged

6. In the "Add someone" panel, submit a new Microsoft account email with only the Player role
   checked and confirm it appears in the table with a `Player` tag and a "Never signed in"
   status.
7. Attempt to submit with neither role checked and confirm the existing "select at least one
   role" validation still blocks it.
8. Select **Remove** on a removable row and confirm the confirmation dialog names the account;
   confirm **Keep it** leaves it in the table, and confirming **Remove account** removes it.

## Validate refresh

9. Select the header's Refresh control and confirm the table re-reads from the server without
   navigating away from the People screen.

## Validate the shared button language

10. Visit another screen using `.btn-primary`/`.btn-secondary`/`.btn-ghost` (e.g. Home's
    "Start a new adventure" button, or the admin Stories list's row actions) and confirm those
    buttons now show a visible 2px border at rest and the updated hover/press treatment — this
    feature's `designTokens.css` change is app-wide, not scoped to People (research.md
    Decision 4).

## Automated tests

```bash
# Backend
cd src/backend && pytest tests/integration/test_admin_accounts_endpoint.py

# Frontend
cd src/frontend && npx vitest run tests/components/AccountList.test.jsx \
  tests/components/AccountForm.test.jsx \
  tests/integration/admin_accounts.test.jsx \
  tests/integration/admin_accounts_refresh.test.jsx
```
