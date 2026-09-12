import { useEffect, useRef } from "react";

/**
 * Save-before-sign-out prompt (009-save-and-continue, FR-004, FR-005) — offered only
 * when the player has an active game in progress (NavBar decides that). Progress is
 * already autosaved every turn, so this is purely about recording an extra, labelled
 * checkpoint; declining loses nothing. Matches PauseDialog's dialog/dialog-backdrop
 * pattern.
 */
export function LogoutSavePrompt({ saving, failureMessage, onSave, onDontSave, onCancel }) {
  const dialogRef = useRef(null);

  useEffect(() => {
    dialogRef.current?.focus();
  }, []);

  const handleKeyDown = (event) => {
    if (event.key === "Escape" && !saving) {
      event.preventDefault();
      event.stopPropagation();
      onCancel();
    }
  };

  return (
    <div className="dialog-backdrop">
      <div
        ref={dialogRef}
        className="dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="logout-save-prompt-title"
        tabIndex={-1}
        style={{ width: "min(520px,100%)", padding: "32px" }}
        onKeyDownCapture={handleKeyDown}
      >
        <div className="dialog-title" id="logout-save-prompt-title" style={{ fontSize: "24px" }}>
          Save before you go?
        </div>
        <div className="dialog-body">
          Your progress is already safe — every turn is saved as you play. Recording a checkpoint just marks this
          exact spot to come back to.
        </div>
        {failureMessage && (
          <p role="alert" className="text-muted" style={{ fontSize: "13px", margin: "12px 0 0" }}>
            {failureMessage}
          </p>
        )}
        <hr className="hr" style={{ margin: "6px 0" }} />
        <button
          className="btn btn-primary btn-block"
          type="button"
          style={{ padding: "14px 16px", fontSize: "16px", margin: 0 }}
          onClick={onSave}
          disabled={saving}
        >
          Save and sign out
        </button>
        <button
          className="btn btn-secondary btn-block"
          type="button"
          style={{ padding: "14px 16px", margin: "10px 0 0" }}
          onClick={onDontSave}
          disabled={saving}
        >
          Sign out without saving
        </button>
        <button
          className="btn btn-secondary btn-block"
          type="button"
          style={{ padding: "14px 16px", margin: "10px 0 0" }}
          onClick={onCancel}
          disabled={saving}
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

export default LogoutSavePrompt;
