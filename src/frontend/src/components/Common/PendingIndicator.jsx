import { Spinner } from "./PendingButton.jsx";

/**
 * The non-button half of the pending-action pattern (issue #347): an async backend call
 * that no single control owns — a screen's initial load, a refresh, a turn the story
 * engine is still writing — still has to say on screen that something is happening.
 *
 * `PendingButton` covers the case where the user actioned a control and that control can
 * speak for itself; this covers everything else. Both render the same `.spinner`, so a
 * slow call reads the same way wherever it happens.
 *
 * `role="status"` (an implicit `aria-live="polite"`) rather than plain text: these appear
 * and disappear without the user acting, so a screen reader has to be told.
 */
export function PendingIndicator({ children = "Loading…", className = "text-muted", style }) {
  return (
    <p role="status" className={`pending-indicator ${className}`.trim()} style={style}>
      <Spinner />
      <span>{children}</span>
    </p>
  );
}

export default PendingIndicator;
