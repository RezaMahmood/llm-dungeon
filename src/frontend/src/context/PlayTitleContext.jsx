import { createContext, useContext, useEffect, useMemo, useState } from "react";

/**
 * Lets the play surface publish its story title and pause-and-exit handler up to the
 * `TitleBar` that `AuthenticatedLayout` renders as its sibling (not its parent) — the
 * same shape as `RefreshContext`.
 *
 * Without this the play page has no way to reach the header, so it grows its own — which
 * is how a second, unconfirmed "Pause & exit" ended up on the play screen, breaking
 * FR-016/SC-013's "no path that exits without that confirmation".
 */
const PlayTitleContext = createContext(null);

export function PlayTitleProvider({ children }) {
  const [value, setValue] = useState(null);

  const contextValue = useMemo(() => ({ value, setValue }), [value]);

  return <PlayTitleContext.Provider value={contextValue}>{children}</PlayTitleContext.Provider>;
}

/**
 * Called by the play page with its title and exit handler. Publishes them while mounted
 * and clears them on unmount, so navigating away returns the header to its plain state.
 * `onPauseExit` must be referentially stable (wrap it in `useCallback`).
 */
export function usePublishPlayTitle({ storyTitle, onPauseExit }) {
  const ctx = useContext(PlayTitleContext);
  const setValue = ctx?.setValue;

  useEffect(() => {
    setValue?.({ storyTitle, onPauseExit });
    return () => setValue?.(null);
  }, [setValue, storyTitle, onPauseExit]);
}

/** Called by `TitleBar` to read what the play page published, if anything. */
export function usePlayTitle() {
  const ctx = useContext(PlayTitleContext);
  return ctx ? ctx.value : null;
}

export default PlayTitleContext;
