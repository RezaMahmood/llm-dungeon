import "./Play.css";

/**
 * Status panel: location, goal, and chapter progress from the latest turn
 * (specs/designs/03-play.html). When the session has concluded, also shows the
 * ending reason (FR-009's duration/success/failure outcome).
 */
const REASON_LABELS = {
  duration: "Time ran out",
  success: "You succeeded",
  failure: "You did not succeed",
};

export function StatusPanel({ locationLabel, goalLabel, progress, completionReason }) {
  return (
    <div className="play-panel">
      <div className="play-label">Where you are</div>
      <div className="play-location">{locationLabel}</div>

      {goalLabel && (
        <>
          <hr className="hr" style={{ margin: "20px 0", height: "1px" }} />
          <div className="play-label">Your goal</div>
          <p className="play-goal">{goalLabel}</p>
        </>
      )}

      {progress && (
        <>
          <hr className="hr" style={{ margin: "20px 0", height: "1px" }} />
          <div className="play-label">Progress</div>
          <div className="play-progress-row">
            <span className="ovnum" style={{ fontSize: "52px", color: "var(--color-accent)" }}>
              {progress.current}
            </span>
            <span className="text-muted" style={{ fontSize: "13px", paddingBottom: "8px" }}>
              of {progress.total} chapters
            </span>
          </div>
          {/* The numeral/text above already carries the "3 of 5" meaning in text, so the
              bar itself is a visual reinforcement, never the only place the count lives
              (constitution, Accessibility — meaning is never carried by color alone). */}
          <div className="progress-bars" style={{ marginTop: "10px" }}>
            {Array.from({ length: progress.total }, (_, index) => (
              <span key={index} className={index < progress.current ? "filled" : undefined} />
            ))}
          </div>
        </>
      )}

      {completionReason && (
        <>
          <hr className="hr" style={{ margin: "20px 0", height: "1px" }} />
          <div className="play-label">The story has ended</div>
          <p style={{ margin: "8px 0 0", fontSize: "15px", lineHeight: 1.5 }} role="status">
            {REASON_LABELS[completionReason.type] || "The story ended"}
            {completionReason.detail ? ` — ${completionReason.detail}` : ""}
          </p>
        </>
      )}

      {/* FR-017: the play surface states that progress is autosaved after every turn.
          specs/designs/03-play.html places this at the foot of the status panel. */}
      <div className="text-muted play-autosave">Autosaved after every turn</div>
    </div>
  );
}

export default StatusPanel;
