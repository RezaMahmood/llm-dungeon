/**
 * Pause-and-exit confirmation (FR-016, Constitution "Save and session behaviour" #3) —
 * exiting the play surface never happens unconfirmed. Matches
 * specs/designs/03-play.html's pause dialog.
 */
export function PauseDialog({ locationLabel, onKeepPlaying, onConfirmExit }) {
  return (
    <div className="dialog-backdrop">
      <div className="dialog" style={{ width: "min(520px,100%)", padding: "32px" }}>
        <div className="ovnum" style={{ fontSize: "72px", color: "var(--color-accent)" }}>
          II
        </div>
        <div className="dialog-title" style={{ fontSize: "28px" }}>
          Paused
        </div>
        <div className="dialog-body">
          Your story is saved{locationLabel ? ` at ${locationLabel}` : ""}. Come back whenever — nothing moves
          without you.
        </div>
        <hr className="hr" style={{ margin: "6px 0" }} />
        <button
          className="btn btn-primary btn-block"
          type="button"
          style={{ padding: "14px 16px", fontSize: "16px", margin: 0 }}
          onClick={onKeepPlaying}
        >
          Keep playing
        </button>
        <button
          className="btn btn-secondary btn-block"
          type="button"
          style={{ padding: "14px 16px", margin: 0 }}
          onClick={onConfirmExit}
        >
          Save and exit to my stories
        </button>
      </div>
    </div>
  );
}

export default PauseDialog;
