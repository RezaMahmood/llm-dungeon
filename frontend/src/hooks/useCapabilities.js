import { useMsal } from "@azure/msal-react";
import { useCallback, useEffect, useState } from "react";

import { getMe } from "../services/authService.js";
import { loginRequest } from "../services/msalConfig.js";

/**
 * Fetches the current user's capabilities from GET /api/auth/me.
 * Returns { hasPlayer, hasAdministrator, loading, error, denied, refetch }.
 */
export function useCapabilities() {
  const { instance, accounts } = useMsal();
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

  const fetchCapabilities = useCallback(async () => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const tokenResponse = await instance.acquireTokenSilent({
        ...loginRequest,
        account,
      });
      const data = await getMe(tokenResponse.accessToken);
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
        await instance.loginRedirect(loginRequest);
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
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- `account` is intentionally
    // excluded: only `accountKey` (a stable primitive) should re-create this callback.
  }, [instance, accountKey]);

  useEffect(() => {
    fetchCapabilities();
  }, [fetchCapabilities]);

  return { ...state, refetch: fetchCapabilities };
}

export default useCapabilities;
