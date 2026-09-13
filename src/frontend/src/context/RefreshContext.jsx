import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

/**
 * Lets a page publish its `useRefreshable` state up to `NavBar`/`TitleBar`,
 * which render as its sibling (not its parent) under `AuthenticatedLayout`
 * (contracts/refresh-control.md's `RefreshContext` section).
 */
const RefreshContext = createContext(null);

export function RefreshProvider({ children }) {
  const [value, setValue] = useState(null);

  const contextValue = useMemo(() => ({ value, setValue }), [value]);

  return <RefreshContext.Provider value={contextValue}>{children}</RefreshContext.Provider>;
}

/**
 * Called by the currently-mounted page with its `useRefreshable` output.
 * Publishes `{ refresh, loading, disabled }` while mounted; clears it on unmount so
 * navigating away removes the control from the nav bar before the next
 * page's own effect runs.
 *
 * `loading` means a refresh is actually in flight — the control spins and says so.
 * `disabled` (optional) only makes it inert, for a page that has some *other* call
 * running that a refresh must not race.
 */
export function usePublishRefresh({ refresh, loading, disabled = false }) {
  const ctx = useContext(RefreshContext);
  const setValue = ctx?.setValue;

  const publish = useCallback(() => {
    setValue?.({ refresh, loading, disabled });
  }, [setValue, refresh, loading, disabled]);

  useEffect(() => {
    publish();
    return () => setValue?.(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- `publish` already tracks refresh/loading
  }, [publish]);
}

/** Called by `NavBar`/`TitleBar` to read the currently-published refresh state, if any. */
export function useRefreshContext() {
  const ctx = useContext(RefreshContext);
  return ctx ? ctx.value : null;
}

export default RefreshContext;
