import { useDeleteSession } from "../../hooks/useDeleteSession.js";

/**
 * Permanent delete for one saved session plus its confirmation dialog
 * (028-home-page-redesign FR-008/FR-009), mirroring
 * `Admin/StoryDeleteAction.jsx`'s dialog pattern (Principle VIII) — the canonical mockup's
 * `confirm()` is a static-prototype artifact, not the design's actual mechanism
 * (research.md Decision 6).
 *
 * Sits inside `SessionCard`'s whole-card `<a>` (resume link), so both the trigger and the
 * dialog's own controls stop the click from also firing that link.
 *
 * `token` may be a plain access-token string or an async function returning one, matching
 * `StoryDeleteAction`'s own `token` contract.
 */
export function SessionDeleteAction({ session, token, onDeleted }) {
  const { status, confirmingDelete, requestDelete, confirmDelete, cancelDelete } = useDeleteSession(
    token,
    session,
    onDeleted,
  );

  const title = session.adventureName || "this story";
  const dialogTitleId = `delete-session-dialog-title-${session.sessionId}`;

  const stopAndRun = (handler) => (event) => {
    event.preventDefault();
    event.stopPropagation();
    handler();
  };

  return (
    <>
      <span
        className="home-btn-danger btn"
        role="button"
        tabIndex={0}
        title="Delete this session"
        aria-label="Delete this session"
        style={{ padding: "9px 12px", fontSize: "13px", gap: "6px" }}
        onClick={stopAndRun(requestDelete)}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ") stopAndRun(requestDelete)(event);
        }}
      >
        Delete
      </span>

      {status === "error" && (
        <div role="alert" className="text-muted" style={{ fontSize: "12px", marginTop: "4px" }}>
          Could not delete this session. Please try again.
        </div>
      )}

      {confirmingDelete && (
        <div className="dialog-backdrop" onClick={stopAndRun(cancelDelete)}>
          <div
            className="dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby={dialogTitleId}
            onClick={(event) => event.stopPropagation()}
          >
            <div className="dialog-title" id={dialogTitleId}>
              Delete your saved session for &ldquo;{title}&rdquo;?
            </div>
            <div className="dialog-body">Your progress will be lost.</div>
            <div className="dialog-actions">
              <button type="button" className="btn btn-secondary" onClick={stopAndRun(cancelDelete)} disabled={status === "working"}>
                Cancel
              </button>
              <button type="button" className="btn btn-primary" onClick={stopAndRun(confirmDelete)} disabled={status === "working"}>
                {status === "working" ? "Deleting…" : "Delete"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export default SessionDeleteAction;
