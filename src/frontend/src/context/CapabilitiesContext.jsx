import { useMsal } from "@azure/msal-react";
import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { getMe } from "../services/authService.js";
import { loginRequest } from "../services/msalConfig.js";

// Guards against a redirect loop: if /api/auth/me keeps 401ing even after an
// interactive sign-in (e.g. a structural token problem, not just a stale
// session), redirecting to Microsoft's login on every 401 fires repeatedly in
// quick succession — enough to trip Entra ID's own throttling/lockout
// protection on the account. Cleared on a successful fetch so a real future
// session can still retry once.
const REDIRECT_ATTEMPTED_KEY = "llmdungeon.capabilities.redirectAttempted";

/**
 * One shared fetch of the current user's capabilities, mounted once near the
 * app root (App.jsx). Previously every consumer (ProtectedRoute, NavBar,
 * MainMenu) called its own independent `useCapabilities()` instance, each
 * firing its own /api/auth/me request on mount — on a hard reload these raced
 * each other, and a component reading a still-default `hasAdministrator: false`
 * from its own not-yet-resolved instance could render "Access not granted"
 * even though a sibling instance's request had already come back granting
 * access (found via the user's own T024 walkthrough, 2026-08-31: reloading
 * any Administrator-only route showed "Access not granted" despite
 * /api/auth/me genuinely returning hasAdministrator: true). A single shared
 * fetch removes the race entirely, and also means MainMenu's refresh control
 * updates NavBar's admin/player links too, not just its own content (FR-011).
 */
const CapabilitiesContext = createContext(null);

export function CapabilitiesProvider({ children }) {
  const { instance, accounts } = useMsal();
  const navigate = useNavigate();
  const account = accounts[0];
  // Depend on a stable primitive rather than the `accounts` array/object
  // reference, which some MSAL context updates (and test mocks) can recreate
  // every render — depending on the reference directly causes fetchCapabilities
  // to be re-created every render, re-triggering the effect below in a loop.
  const accountKey = account?.homeAccountId ?? account?.username ?? null;
  const [state, setState] = useState({
    hasPlayer: false,
    hasAdministrator: false,
    loading: true,
    error: null,
    denied: false,
  });
  const loadingRef = useRef(false);

  const fetchCapabilities = useCallback(async () => {
    if (loadingRef.current) return;
    // Not signed in yet (or MSAL hasn't hydrated its cached account from
    // localStorage yet on a hard reload) — nothing to fetch. `accountKey`
    // changing once an account appears re-creates this callback and the
    // effect below re-runs it.
    if (!account) return;
    loadingRef.current = true;
    setState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      let tokenResponse;
      try {
        tokenResponse = await instance.acquireTokenSilent({
          ...loginRequest,
          account,
        });
      } catch (err) {
        // MSAL couldn't silently renew the cached session client-side (e.g. an
        // expired/invalid refresh token after time away, or a consent/MFA
        // step-up now required) — this fails before ever reaching the backend,
        // so it never shows up as a 401 from /api/auth/me below. Found via the
        // user's own T024 walkthrough (2026-09-01): a hard reload showed
        // "Access not granted" with zero /api/auth/me requests in the network
        // panel — this exact path, previously falling through to the generic
        // error branch and leaving hasAdministrator at its false default.
        // Needs the same "explain before re-auth" handling as a backend 401
        // (contracts/reload-resilience.md Guarantee 3, FR-008).
        if (sessionStorage.getItem(REDIRECT_ATTEMPTED_KEY)) {
          setState({
            hasPlayer: false,
            hasAdministrator: false,
            loading: false,
            error: err,
            denied: false,
          });
          return;
        }
        sessionStorage.setItem(REDIRECT_ATTEMPTED_KEY, "1");
        navigate("/login", { state: { reason: "session-expired" } });
        setState((prev) => ({ ...prev, loading: false }));
        return;
      }

      const data = await getMe(tokenResponse.accessToken);
      sessionStorage.removeItem(REDIRECT_ATTEMPTED_KEY);
      setState({
        hasPlayer: Boolean(data.capabilities?.hasPlayer),
        hasAdministrator: Boolean(data.capabilities?.hasAdministrator),
        loading: false,
        error: null,
        denied: false,
      });
    } catch (err) {
      const status = err.response?.status;
      if (status === 401) {
        if (sessionStorage.getItem(REDIRECT_ATTEMPTED_KEY)) {
          setState({
            hasPlayer: false,
            hasAdministrator: false,
            loading: false,
            error: err,
            denied: false,
          });
          return;
        }
        sessionStorage.setItem(REDIRECT_ATTEMPTED_KEY, "1");
        // Route to our own /login with an explanation before any automatic
        // re-authentication attempt (contracts/reload-resilience.md Guarantee 3,
        // FR-008) — rather than bouncing straight to Microsoft's hosted sign-in.
        navigate("/login", { state: { reason: "session-expired" } });
        setState((prev) => ({ ...prev, loading: false }));
        return;
      }
      if (status === 403) {
        setState({
          hasPlayer: false,
          hasAdministrator: false,
          loading: false,
          error: null,
          denied: true,
        });
        return;
      }
      setState((prev) => ({ ...prev, loading: false, error: err }));
    } finally {
      loadingRef.current = false;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- `account` is intentionally
    // excluded: only `accountKey` (a stable primitive) should re-create this callback.
  }, [instance, accountKey, navigate]);

  useEffect(() => {
    fetchCapabilities();
  }, [fetchCapabilities]);

  const value = { ...state, refetch: fetchCapabilities };

  return <CapabilitiesContext.Provider value={value}>{children}</CapabilitiesContext.Provider>;
}

/**
 * Reads the shared capabilities state. Must be used under `CapabilitiesProvider`
 * (mounted once in App.jsx, above the route tree) — every consumer shares one
 * fetch instead of each racing its own.
 */
export function useCapabilities() {
  const ctx = useContext(CapabilitiesContext);
  if (!ctx) {
    throw new Error("useCapabilities must be used within a CapabilitiesProvider");
  }
  return ctx;
}

export default useCapabilities;
