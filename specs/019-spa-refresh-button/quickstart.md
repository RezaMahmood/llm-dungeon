# Quickstart: Validate In-App Screen Refresh & Reload Resilience

**Date**: 2026-08-30

**Feature**: In-App Screen Refresh & Reload Resilience (019-spa-refresh-button)

This guide provides step-by-step validation scenarios confirming the feature works end-to-end. See [contracts/refresh-control.md](contracts/refresh-control.md) and [contracts/reload-resilience.md](contracts/reload-resilience.md) for the exact behavior contracts and [data-model.md](data-model.md) for the underlying state shape.

---

## Prerequisites

1. Frontend deployed to (or served from a build that mirrors) Azure Static Web Apps, with `staticwebapp.config.json` included in the deployed output — a local Vite dev server does not exercise Guarantee 1 in `contracts/reload-resilience.md`, since its fallback behavior differs from the real platform.
2. A signed-in test account with both Player and Administrator capabilities (so `/menu`, `/admin/accounts`, and `/admin/stories/new` are all reachable).
3. Browser dev tools available to simulate a slow/failed network request (e.g., Chrome DevTools' Network throttling/"Offline" toggle) and to inspect `localStorage` for the MSAL token cache.

---

## Scenario 1: In-app refresh updates data without leaving the screen (User Story 1, FR-001/FR-002/FR-003)

**Steps**:
1. Sign in and navigate to Admin → Accounts.
2. In another tab/session (or directly via the API), add a new account.
3. On the Accounts screen, select the refresh control.

**Expected**: The new account appears in the list; the URL and screen do not change; the user is not signed out.

---

## Scenario 2: Overlapping refresh is prevented (FR-004)

**Steps**:
1. On Admin → Accounts, throttle the network to add latency.
2. Select the refresh control, then immediately select it again before the first request completes.

**Expected**: Only one request is observed in the network panel; the control shows an in-progress state throughout; no duplicate/overlapping fetch occurs.

---

## Scenario 3: A failed refresh shows a clear, recoverable error (FR-005)

**Steps**:
1. On Admin → Accounts (data already loaded), switch DevTools to "Offline."
2. Select the refresh control.

**Expected**: An inline, non-blocking error message appears; the previously-loaded account list remains visible (screen does not blank or crash); switching back online and retrying succeeds.

---

## Scenario 4: Browser reload on a nested route does not error (User Story 2, FR-006, SC-003)

**Steps**:
1. Sign in and navigate to Admin → New story (`/admin/stories/new`).
2. Use the browser's native reload (not the in-app control).

**Expected**: The same wizard screen loads again with no browser- or application-level error page. (This is the scenario Guarantee 1 in `contracts/reload-resilience.md` exists for — verify against the real deployed Static Web App, not only a local dev server.)

---

## Scenario 5: A valid session survives a reload with no re-authentication (FR-007, FR-009, SC-004)

**Steps**:
1. Sign in, navigate to any authenticated screen.
2. Reload the browser natively.

**Expected**: The same screen loads with the user still signed in — no redirect to Microsoft's sign-in page, no interactive prompt, no visible authentication flash beyond a brief loading state.

---

## Scenario 6: An expired session on reload gets a clear explanation (FR-008)

**Steps**:
1. Sign in, then invalidate the session server-side (e.g., remove the account's provisioning entry, or clear/expire the token via DevTools' Application → Local Storage).
2. Reload the browser natively.

**Expected**: The user lands on the sign-in screen with an explanatory message (not a generic error page), per `contracts/reload-resilience.md` Guarantee 3.

---

## Scenario 7: Unsaved wizard input warns before it's lost (User Story 3, FR-010)

**Steps**:
1. Navigate to Admin → New story and begin typing in a step's field without saving.
2. Attempt to reload or close the tab.

**Expected**: The browser's native "leave site?" confirmation appears. Repeat with no unsaved input (freshly loaded, untouched wizard) and confirm no prompt appears.

---

## Scenario 8: Refreshed data reflects current permissions (FR-011)

**Steps**:
1. Sign in as a user with Administrator access; load the Main Menu.
2. In another session, remove that user's Administrator capability.
3. On the original session's Main Menu, select the refresh control.

**Expected**: The Administrator menu item disappears without requiring a full reload or sign-out; if no capabilities remain, the "Access Provisioned" no-access state is shown instead.

---

## Final acceptance (Constitution Principle IX)

All eight scenarios above MUST be re-verified by the requesting user or product owner against the real deployed environment before this feature is considered complete — per `tasks.md`'s required final acceptance task — not solely on the strength of the automated test suite.
