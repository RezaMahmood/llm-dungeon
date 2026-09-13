/**
 * Shown on Home when a player is returned here because the session they were playing has
 * been deleted (031-sessions-admin-design-spec FR-012/FR-013).
 *
 * Names no actor: the application cannot tell an administrator's delete from this
 * player's own delete in another tab, and claiming one would be a fabrication
 * (research.md Decision 4). Built from the design system's dialog primitives; not
 * `ConfirmDeleteDialog`, which is a two-action confirmation — this is an acknowledgement
 * of something that has already happened.
 */
export function SessionRemovedDialog({ onDismiss }) {
  return (
    <div className="dialog-backdrop" onClick={onDismiss}>
      <div
        className="dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="session-removed-title"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="dialog-title" id="session-removed-title">
          This session has been removed
        </div>
        <div className="dialog-body">
          Your saved progress for it is gone, so it&rsquo;s no longer in your list. You can start
          the story again whenever you like.
        </div>
        <div className="dialog-actions">
          <button type="button" className="btn btn-primary" onClick={onDismiss} autoFocus>
            Got it
          </button>
        </div>
      </div>
    </div>
  );
}

export default SessionRemovedDialog;
