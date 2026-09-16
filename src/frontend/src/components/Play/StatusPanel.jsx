import "./Play.css";

/**
 * Status panel: location, goal, and chapter progress from the latest turn
 * (specs/designs/03-play.html). When the session has concluded, also shows the
 * ending reason (FR-009's duration/success/failure outcome). When the session carries
 * an avatar description, also shows it read-only (034-avatar-memory-and-visibility
 * FR-001) — absent entirely for a session with none (FR-003).
 */
const REASON_LABELS = {
  duration: "Time ran out",
  success: "You succeeded",
  failure: "You did not succeed",
};

export function StatusPanel({ locationLabel, goalLabel, progress, completionReason, avatarDescription }) {
  return (
    <div className="play-panel">
      <div className="play-label">Where you are</div>
      <div className="play-location">{locationLabel}</div>

      {avatarDescription && (
        <>
          <hr className="hr" style={{ margin: "20px 0", height: "1px" }} />
          <div className="play-label">Who you are</div>
          <p className="play-goal">{avatarDescription}</p>
        </>
      )}

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
          <p className="play-goal" role="status">
            {REASON_LABELS[completionReason.type] || "The story ended"}
            {completionReason.detail ? ` — ${completionReason.detail}` : ""}
          </p>
        </>
      )}

      <hr className="hr" style={{ margin: "20px 0", height: "1px" }} />
      {/*
       * "Stuck? Get a hint" (spec.md FR-007, *Scope note*; research.md Decision 2). The
       * design shows this control; the guidance behind it is a separate, not-yet-built
       * feature, so it ships here as a real, honestly-inert button rather than inventing
       * stand-in behaviour. aria-disabled, never the native `disabled` attribute: a
       * natively disabled button drops out of the tab order and could never show the
       * focus indicator spec.md US2 AS2 and the constitution's Interaction-states rule
       * both require. contracts/ui.md's .btn[aria-disabled="true"] selector (designTokens.css)
       * still gives it the disabled look.
       */}
      <button type="button" className="btn btn-secondary btn-block play-hint" aria-disabled="true">
        Stuck? Get a hint
      </button>
      <p className="text-muted play-hint-pending">Hints are coming soon.</p>

      {/* FR-017: the play surface states that progress is autosaved after every turn.
          specs/designs/03-play.html places this at the foot of the status panel and
          gives it this exact wording (03-play.html:92; SC-003). */}
      <div className="text-muted play-autosave">Saved automatically after every turn.</div>
    </div>
  );
}

export default StatusPanel;
