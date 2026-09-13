import PendingButton from "../Common/PendingButton.jsx";

/**
 * Pause-and-exit confirmation (FR-016, Constitution "Save and session behaviour" #3) —
 * exiting the play surface never happens unconfirmed. Matches
 * specs/designs/03-play.html's pause dialog.
 *
 * `saving`: the exit records a checkpoint first, which is a backend call that can be slow,
 * so the button that was pressed spins and both buttons go inert until it comes back
 * (issue #347) — otherwise the dialog just sits there and the player presses again.
 */
export function PauseDialog({ locationLabel, onKeepPlaying, onConfirmExit, saving = false }) {
  return (
    <div className="dialog-backdrop">
      <div
        className="dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="pause-dialog-title"
        style={{ width: "min(520px,100%)", padding: "32px" }}
      >
        <div className="ovnum" style={{ fontSize: "72px", color: "var(--color-accent)" }}>
          II
        </div>
        <div className="dialog-title" id="pause-dialog-title" style={{ fontSize: "28px" }}>
          Paused
        </div>
        <div className="dialog-body">
          Your story is saved{locationLabel ? ` at ${locationLabel}` : ""}. Come back whenever — nothing moves
          without you.
        </div>
        <hr className="hr" style={{ margin: "6px 0" }} />
        <PendingButton
          className="btn btn-primary btn-block"
          style={{ padding: "14px 16px", fontSize: "16px", margin: 0 }}
          onClick={onKeepPlaying}
          disabled={saving}
        >
          Keep playing
        </PendingButton>
        <PendingButton
          className="btn btn-secondary btn-block"
          style={{ padding: "14px 16px", margin: 0 }}
          onClick={onConfirmExit}
          pending={saving}
          pendingLabel="Saving your story…"
        >
          Save and exit to my stories
        </PendingButton>
      </div>
    </div>
  );
}

export default PauseDialog;
