# UI Contract: Login Screen

**Date**: 2026-08-28

**Feature**: Login and Access Control (002-login-and-access-control)

**Design Reference**: [specs/designs/01-login.html](../../designs/01-login.html)

---

## Overview

The login screen is the entry point for unauthenticated users. It provides a single button to initiate Microsoft Entra ID sign-in flow. The screen enforces the project's design system (per Constitution Principle VIII) and must be accessible and secure.

---

## Screen States

### State 1: Idle (Initial Load)

**Rendering**:
- Title: "LLM Dungeon Adventure" (or project name)
- Subtitle: "Sign in to continue" (or similar welcome message)
- Button: "Sign in with Microsoft"
  - Label color: design-system accent color
  - Background: design-system button base color
  - No other input fields (no username/password; no alternate providers)
- Optional: "Signing you in..." loader message while redirect happens

**User Actions**:
- Click "Sign in with Microsoft" → Triggers MSAL login flow
- Close browser → No state to preserve; fresh sign-in on next visit

**Visual Requirements** (per Constitution):
- Zero corner radius (flush corners)
- Flush-left alignment for text
- Body copy meets 4.5:1 contrast ratio
- No illustrations or emoji
- Focus-visible outline on button with 4px offset

### State 2: Loading (After Click)

**Rendering**:
- Button is disabled (opacity reduced, `cursor: not-allowed`)
- Loader indicator appears (spinner or text: "Redirecting to Microsoft...")
- User cannot click again

**Duration**: <1 second (redirect happens almost immediately)

**Visual Requirements**:
- Loader uses design-system colors (not custom spinners)
- Text remains readable throughout transition

### State 3: Sign-In Cancelled

**Rendering** (if user closes the identity provider's login window or cancels):
- Return to State 1 (Idle)
- Display a dismissible message: "Sign in was cancelled. Please try again."
- Button remains active

**Duration**: Message auto-dismisses after 3 seconds or on user click

**Visual Requirements**:
- Error message uses a distinct (but not red-only) color from design system
- Meaning is conveyed by text + icon, not color alone

### State 4: Sign-In Failed (Network Error)

**Rendering** (if MSAL encounters a network error):
- Return to State 1 (Idle)
- Display an error message: "Sign in failed. Please check your connection and try again."
- Button remains active
- Optional: Show error details in a collapsible section (for debugging)

**Duration**: Message remains until user dismisses or closes browser

**Visual Requirements**:
- Same as State 3 (error message styling)

### State 5: Sign-In Succeeded (After Token Acquired)

**Rendering**:
- Frontend receives token from MSAL
- Call `/api/auth/me` to fetch capabilities
- Transition to main application shell (menu screen or game screen, depending on capabilities)

**Duration**: <500ms (API call + page navigation)

**Visual Requirements**:
- Smooth fade or navigation transition
- No jarring layout shifts

### State 6: Access Denied (After Sign-In)

**Rendering** (if token is valid but user is not on allow-list):
- Display a full-page message:
  - Title: "Access Not Granted"
  - Body: "This account does not have access to LLM Dungeon Adventure. If you believe this is an error, please contact your administrator."
  - Button: "Sign in with a different account"
- Clicking button triggers MSAL logout + login again (allow user to try with different account)

**Visual Requirements**:
- Centered layout (exception to flush-left alignment for this critical message)
- High contrast, large text
- Clear next action (try again)

### State 7: No Capabilities (User Allowed but No Roles)

**Rendering** (if token is valid, user is on allow-list, but has no capabilities):
- Display a full-page message:
  - Title: "Access Provisioned"
  - Body: "Your account has been registered but no roles have been assigned yet. Please contact your administrator to grant access."
  - Button: "Sign out" or "Try again" (retry the capabilities fetch)

**Visual Requirements**:
- Same as State 6
- Clear explanation (this is not an error, but a configuration state)

---

## Interaction Requirements

**Keyboard Navigation**:
- Tab focus cycles to the sign-in button
- Enter/Space triggers sign-in
- Focus-visible outline is always visible when button is focused

**Touch/Mobile**:
- Button is at least 44px tall (per accessibility guidelines)
- Touch target is full button width and height (no small click areas)

**Viewport Responsiveness**:
- Minimum width: 320px (mobile portrait)
- Minimum height: 480px (mobile landscape)
- Text remains legible and button remains accessible down to 320px width
- No horizontal scroll required at any viewport size

---

## Error Messages and Copy

All copy is user-facing, warm, and plain (per Constitution Principle VIII):

| State | Message | Tone |
|-------|---------|------|
| Cancelled | "Sign in was cancelled. Please try again." | Neutral, no blame |
| Network Error | "Sign in failed. Please check your connection and try again." | Helpful, actionable |
| Access Denied | "This account does not have access to LLM Dungeon Adventure. If you believe this is an error, please contact your administrator." | Clear, no shame |
| No Capabilities | "Your account has been registered but no roles have been assigned yet. Please contact your administrator to grant access." | Explanatory, not punitive |

---

## Design System Compliance

**Colors** (from `specs/designs/styles.css`):
- Primary button: `--button-color-base` or equivalent
- Accent on hover: `--button-color-hover`
- Accent on press: `--button-color-active`
- Focus outline: `--color-accent` with `--space-2` offset
- Text: `--color-text-primary` (4.5:1 contrast)
- Error messages: use `--color-status-error` + text (not color alone)

**Typography** (from `specs/designs/styles.css`):
- Heading: `--font-heading` at `--font-size-lg`
- Body: `--font-body` at `--font-size-base`
- Line-height: generous (1.5 or higher) for readability

**Spacing** (from `specs/designs/styles.css`):
- Page padding: `--space-4` or `--space-6`
- Button margin-top: `--space-4`
- Message padding: `--space-4`

**Layout**:
- Centered vertical flex layout (no grid or floats)
- Zero corner radius (all elements flush-cornered)
- Visible dividing rule between title and form (if desired; not strictly required)

---

## Accessibility Checklist

- [ ] Button text is clear and describes the action ("Sign in with Microsoft", not "Login")
- [ ] Focus-visible outline is present on button
- [ ] Color is not the only way to convey information (errors use text + icon/badge)
- [ ] Minimum touch target is 44x44px
- [ ] Text meets 4.5:1 contrast ratio
- [ ] Page is fully keyboard-operable (Tab, Enter, Escape to dismiss modals)
- [ ] ARIA labels or semantic HTML (real `<button>`, real `<input>` if any)
- [ ] No auto-playing audio or video
- [ ] Error messages are announced to screen readers (use `role="alert"` or `aria-live="polite"`)

---

## Implementation Notes

### Frontend Component Structure (React)

```jsx
function LoginScreen() {
  const [state, setState] = useState('idle'); // idle, loading, cancelled, failed, denied, no_capabilities
  const [errorMessage, setErrorMessage] = useState('');
  
  const handleSignIn = async () => {
    setState('loading');
    try {
      const result = await msalInstance.loginPopup(...);
      const user = await fetchAuthMe(result.accessToken);
      // Navigate to main app or error state based on user.capabilities
    } catch (err) {
      if (err.errorCode === 'user_cancelled_login') {
        setState('cancelled');
        setErrorMessage('Sign in was cancelled. Please try again.');
      } else {
        setState('failed');
        setErrorMessage('Sign in failed. Please check your connection and try again.');
      }
    }
  };
  
  return (
    <div className="login-screen">
      {state === 'idle' && (
        <>
          <h1>LLM Dungeon Adventure</h1>
          <p>Sign in to continue</p>
          <button onClick={handleSignIn} className="button-primary">
            Sign in with Microsoft
          </button>
        </>
      )}
      {(state === 'cancelled' || state === 'failed') && (
        <div role="alert" className="message-error">
          {errorMessage}
        </div>
      )}
      {state === 'denied' && (
        <div className="message-error">
          <h2>Access Not Granted</h2>
          <p>This account does not have access...</p>
          <button onClick={handleTryAgain}>Sign in with a different account</button>
        </div>
      )}
      {/* ... other states ... */}
    </div>
  );
}
```

### Testing Scenarios

1. **Happy path**: Click button → MSAL opens → User signs in → Token acquired → Navigate to game
2. **Cancelled sign-in**: Click button → MSAL opens → User closes window → Show "cancelled" message
3. **Network error**: Click button → Network fails → Show "network error" message
4. **Access denied**: Click button → MSAL succeeds → API returns 403 → Show "access denied" screen
5. **No capabilities**: Click button → MSAL succeeds → API returns 403 with no_capabilities → Show "no capabilities" screen

---

## Design File Reference

The acceptance prototype for this screen is at:
- **File**: `specs/designs/01-login.html`
- **Stylesheet**: `specs/designs/styles.css` (vendored design tokens)
- **Notes**: See `specs/designs/README.md` for mapping to specifications
