# UI Contract: Application Menu States

**Date**: 2026-08-28

**Feature**: Login and Access Control (002-login-and-access-control)

**Design Reference**: Main application shell (part of `specs/designs/02-story-select.html` and gameplay screens)

---

## Overview

After successful login, the user is presented with a menu based on their assigned capabilities. The menu shows different items depending on whether the user has Player, Administrator, both, or neither capability.

This contract defines the UI behavior for all capability-based menu permutations, ensuring consistent rendering across the application.

---

## Menu Item Definitions

### Menu Item: Game (Start or Continue)

**Label**: "Start or Continue Game" or "Adventure" (exact wording per application design)

**Destination**: Story/Adventure selection screen (feature 005-story-publishing)

**Requirements**:
- Show ONLY to users with Player capability (`has_player: true`)
- Hide from users without Player capability (`has_player: false`)
- Leading action after login for players

**Interaction**:
- Click → Navigate to story selection screen
- Cursor: default (pointer)
- Focus: visible focus outline per design system

### Menu Item: Administration

**Label**: "Administration" or "Story Admin" (exact wording per application design)

**Destination**: Story authoring/administration page (feature 012-story-editing-and-review or 005-story-publishing)

**Requirements**:
- Show ONLY to users with Administrator capability (`has_administrator: true`)
- Hide from users without Administrator capability (`has_administrator: false`)
- Available only to administrators

**Interaction**:
- Click → Navigate to administration screen
- Cursor: default (pointer)
- Focus: visible focus outline per design system

---

## Menu State Matrix

All combinations of Player and Administrator capabilities:

| User Capabilities | Show Game Menu? | Show Admin Menu? | Example UX |
|-------------------|-----------------|-----------------|-----------|
| Player only | ✓ Yes | ✗ No | User sees only "Start or Continue Game" |
| Administrator only | ✗ No | ✓ Yes | User sees only "Administration" |
| Both Player + Admin | ✓ Yes | ✓ Yes | User sees both menu items |
| Neither (allowed but no roles) | ✗ No | ✗ No | User sees "No access provisioned" message |

---

## State 1: Player Only

**Capabilities**: `has_player: true`, `has_administrator: false`

**Rendered Menu**:
```
┌─────────────────────────────┐
│  Start or Continue Game  →  │
└─────────────────────────────┘
```

**Visual Requirements**:
- Single menu item visible
- Item is prominent (primary button styling)
- No other menu items shown
- No "Administration" link or disabled stub

**User Actions**:
- Click game item → Navigate to story/adventure selection
- No other menu options available

---

## State 2: Administrator Only

**Capabilities**: `has_player: false`, `has_administrator: true`

**Rendered Menu**:
```
┌─────────────────────────────┐
│     Administration  →       │
└─────────────────────────────┘
```

**Visual Requirements**:
- Single menu item visible
- Item is prominent (primary button styling)
- No other menu items shown
- No "Game" link or disabled stub

**User Actions**:
- Click admin item → Navigate to administration/authoring screen
- No other menu options available

---

## State 3: Both Player and Administrator

**Capabilities**: `has_player: true`, `has_administrator: true`

**Rendered Menu**:
```
┌─────────────────────────────┐
│  Start or Continue Game  →  │
├─────────────────────────────┤
│     Administration  →       │
└─────────────────────────────┘
```

**Visual Requirements**:
- Both menu items are visible
- Items are separated by a visible dividing rule (per design system)
- Both items have equal visual weight (not one primary, one secondary)
- Each item has its own click target (not nested)

**User Actions**:
- Click game item → Navigate to story/adventure selection
- Click admin item → Navigate to administration/authoring screen
- Both options are always available in the same session (no re-login required)

---

## State 4: No Capabilities (Allowed but Unprovisioned)

**Capabilities**: `has_player: false`, `has_administrator: false`

**Rendered Menu**:
```
┌──────────────────────────────────────┐
│   Access Provisioned                 │
├──────────────────────────────────────┤
│   Your account is registered but      │
│   no roles have been assigned yet.    │
│   Contact your administrator.         │
└──────────────────────────────────────┘
```

**Visual Requirements**:
- Full-screen message (not a menu item)
- Title explains the situation ("Access Provisioned", not "Access Denied")
- Body text provides actionable next step (contact administrator)
- Message uses design system text styling (not error color, but informational)
- Optional: Show a "Refresh" button to re-check capabilities from backend

**User Actions**:
- No menu items to click
- Click "Refresh" or "Try Again" → Call `/api/auth/me` again to fetch updated capabilities
- Sign out → Clear token and return to login screen
- Reload page → API call in startup logic re-fetches capabilities

**Rationale**:
- This state should be rare (user exists on allow-list but administrator hasn't assigned any roles yet)
- Clear explanation prevents confusion (not "access denied", which sounds like a security rejection)

---

## Capability Change Detection

**Scenario**: User is signed in with Player capability. Administrator adds Administrator capability while user is in the application.

**What happens**:
1. User's current session continues with Player capability (no immediate change)
2. On next page navigation or menu refresh, frontend calls `/api/auth/me`
3. Backend returns updated capabilities: `["Player", "Administrator"]`
4. Frontend re-renders menu to show both items
5. Administration menu item becomes available

**Visual indication**:
- Menu smoothly expands to show administration item (if using dynamic rendering)
- No modal or alert required; change is subtle and progressive

**Reverse scenario**: Administrator removes Player capability while user is viewing a story/game.

**What happens**:
1. Current game page session continues (user can finish their current turn)
2. On next action that requires menu refresh or navigation, API call is made
3. Backend returns 403 Forbidden (user no longer has capability)
4. Frontend navigates back to menu
5. Menu now shows only Administration (or neither if admin removed too)
6. User cannot start a new game or continue existing game (access denied at API level)

---

## Menu Location and Styling

**Menu Placement** (per design system):
- Top-level navigation in application shell
- Always accessible (not hidden in hamburger or collapsible menu)
- Visible on all authenticated pages

**Menu Item Styling** (per Constitution Principle VIII):
- Use design-system button classes
- Each item is a full-width block or clearly clickable region
- Separated by dividing rules (visible horizontal lines, not whitespace alone)
- Zero corner radius (flush corners)
- Focus-visible outline on each item
- Hover state uses design-system accent tint

**Responsive Behavior**:
- On mobile (width < 768px): Menu items remain full-width
- On tablet/desktop: Menu may be presented as a sidebar or top navigation (per application design)
- All items remain accessible at any viewport size

---

## Access Control at Destination

**Important**: Menu gating is not sufficient; backend MUST enforce capability checks at the destination endpoint.

**Example**:
- Frontend hides admin menu item (user is Player only)
- Malicious user manually navigates to `/admin` or calls `/api/admin/stories`
- Backend checks user's capabilities and returns 403 Forbidden
- User cannot access admin features regardless of menu state

**Endpoints and their capability requirements**:
- `GET /api/auth/me` — No capability required (returns what user has)
- `GET /api/game/stories` — Requires Player capability
- `POST /api/game/start` — Requires Player capability
- `GET /api/admin/stories` — Requires Administrator capability
- `POST /api/admin/stories/create` — Requires Administrator capability
- (Other endpoints defined in respective feature specs)

---

## Testing Scenarios

### Test 1: Player Only Can See Game Menu

**Setup**: User has Player capability only

**Steps**:
1. Sign in with Player-capable account
2. Verify menu shows "Start or Continue Game"
3. Verify menu does not show "Administration"
4. Click game menu → Verify navigation succeeds

**Expected**:
- Game menu visible and clickable
- Admin menu not shown
- Navigation to game screen succeeds

### Test 2: Administrator Only Can See Admin Menu

**Setup**: User has Administrator capability only

**Steps**:
1. Sign in with Admin-capable account
2. Verify menu shows "Administration"
3. Verify menu does not show "Start or Continue Game"
4. Click admin menu → Verify navigation succeeds

**Expected**:
- Admin menu visible and clickable
- Game menu not shown
- Navigation to admin screen succeeds

### Test 3: Both Capabilities Show Both Menus

**Setup**: User has both Player and Administrator capabilities

**Steps**:
1. Sign in with dual-capability account
2. Verify menu shows both "Start or Continue Game" and "Administration"
3. Click game menu → Verify navigation to game screen succeeds
4. Return to menu
5. Click admin menu → Verify navigation to admin screen succeeds

**Expected**:
- Both menu items visible
- Both navigations succeed in same session (no re-login required)
- No 403 errors

### Test 4: No Capabilities Shows Provisioning Message

**Setup**: User is on allow-list but has no capabilities assigned

**Steps**:
1. Sign in with allowed-but-unprovisioned account
2. Verify menu shows "Access Provisioned" message
3. Verify no game or admin menu items are shown
4. Administrator assigns Player capability (external action)
5. Click "Refresh" button in menu (or reload page)
6. Verify game menu item now appears

**Expected**:
- "Access Provisioned" message shown
- No menu items available until roles assigned
- Capabilities update is detected on refresh

### Test 5: Capability Change During Session

**Setup**: User signs in with Player capability

**Steps**:
1. Sign in and navigate to game story selection
2. Administrator removes Player capability (external action)
3. User attempts to click "Start Game" or navigates back to menu
4. Verify error message and inability to start game

**Expected**:
- API call returns 403 Forbidden
- User cannot proceed with game action
- Menu updates to show no game menu item (or takes effect on next menu refresh)

### Test 6: Direct URL Bypass Prevented

**Setup**: User has Player capability only

**Steps**:
1. Sign in as Player-only user
2. Open browser console and call `fetch('/api/admin/stories')`
3. Verify request returns 403 Forbidden (not 200 OK)

**Expected**:
- Backend enforces capability check at endpoint level
- Menu gating alone is not sufficient
- Attempted bypass is denied with 403

---

## Copy and Messaging

**Menu item labels**:
- "Start or Continue Game" or "Adventure" (exact wording per application design)
- "Administration" or "Story Admin" (exact wording per application design)

**Provisioning message title**: "Access Provisioned"

**Provisioning message body**: "Your account is registered but no roles have been assigned yet. Contact your administrator to grant access."

**No other error messages in menu** (errors are handled at login or destination endpoints)

---

## Accessibility Requirements

- [ ] Menu items are real `<button>` or `<a>` elements (semantic HTML)
- [ ] Each menu item has a visible focus-visible outline
- [ ] Menu items are keyboard-navigable (Tab to cycle, Enter to activate)
- [ ] Menu items meet 4.5:1 contrast ratio for text
- [ ] Menu items are at least 44x44px touch target
- [ ] Dividing rules are visible (not relying on color alone)
- [ ] Provisioning message is not styled as error (text makes meaning clear)
- [ ] Menu updates are announced to screen readers (use `aria-live="polite"` if dynamic)

---

## Future Enhancements (Not in MVP)

These features are NOT required for this specification but are documented for future reference:

- **Personalization**: Menu items could be reordered per user preference
- **Role visibility**: Show user's assigned roles in menu (e.g., "Player • Administrator")
- **Menu icons**: Add icons to menu items (per design system icon set)
- **Submenu nesting**: If more capabilities are added in future, submenu structure might be needed
- **Role-based menu ordering**: Prioritize most-used capability first
