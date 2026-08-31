import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Shared in-flight-guarded refresh state for a screen's data (FR-002, FR-004,
 * FR-005; contracts/refresh-control.md). `fetchFn` should be a stable
 * (`useCallback`-wrapped) async function — its identity re-running the
 * mount-time fetch is the intended behavior, matching the existing
 * `useEffect(() => { refresh(); }, [refresh])` pattern already used by
 * `useCapabilities`/`AdminAccountsPage`.
 */
export function useRefreshable(fetchFn) {
  const [state, setState] = useState({ data: null, loading: true, error: null });
  const loadingRef = useRef(false);

  const refresh = useCallback(async () => {
    if (loadingRef.current) return;
    loadingRef.current = true;
    setState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const data = await fetchFn();
      setState({ data, loading: false, error: null });
    } catch (error) {
      setState((prev) => ({ ...prev, loading: false, error }));
    } finally {
      loadingRef.current = false;
    }
  }, [fetchFn]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { ...state, refresh };
}

export default useRefreshable;
