import { useMsal } from "@azure/msal-react";
import { useCallback, useEffect, useRef, useState } from "react";
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
 * Fetches the current user's capabilities from GET /api/auth/me.
 * Returns { hasPlayer, hasAdministrator, loading, error, denied, refetch }.
 */
export function useCapabilities() {
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
  // MainMenu publishes `refetch` straight into RefreshContext as its shared
  // nav refresh control (rather than wrapping it in useRefreshable), so this
  // hook needs its own in-flight guard to satisfy FR-004 on that path too.
  const loadingRef = useRef(false);

  const fetchCapabilities = useCallback(async () => {
    if (loadingRef.current) return;
    loadingRef.current = true;
    setState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const tokenResponse = await instance.acquireTokenSilent({
        ...loginRequest,
        account,
      });
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
    // `account` is intentionally excluded: only `accountKey` (a stable primitive)
    // should re-create this callback.
  }, [instance, accountKey, navigate]);

  useEffect(() => {
    fetchCapabilities();
  }, [fetchCapabilities]);

  return { ...state, refetch: fetchCapabilities };
}

export default useCapabilities;
