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
      const account = accounts[0];
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
  }, [instance, accounts]);

  useEffect(() => {
    fetchCapabilities();
  }, [fetchCapabilities]);

  return { ...state, refetch: fetchCapabilities };
}

export default useCapabilities;
