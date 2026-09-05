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
    <div style={{ padding: "24px 20px", display: "flex", flexDirection: "column", overflow: "auto" }}>
      <div
        style={{
          fontSize: "11px",
          letterSpacing: "0.1em",
          textTransform: "uppercase",
          color: "color-mix(in srgb, var(--color-text) 50%, transparent)",
        }}
      >
        Where you are
      </div>
      <div style={{ fontFamily: "var(--font-heading)", fontWeight: 800, fontSize: "22px", marginTop: "6px" }}>
        {locationLabel}
      </div>

      {goalLabel && (
        <>
          <hr className="hr" style={{ margin: "20px 0", height: "1px" }} />
          <div
            style={{
              fontSize: "11px",
              letterSpacing: "0.1em",
              textTransform: "uppercase",
              color: "color-mix(in srgb, var(--color-text) 50%, transparent)",
            }}
          >
            Your goal
          </div>
          <p style={{ margin: "8px 0 0", fontSize: "15px", lineHeight: 1.5 }}>{goalLabel}</p>
        </>
      )}

      {progress && (
        <>
          <hr className="hr" style={{ margin: "20px 0", height: "1px" }} />
          <div
            style={{
              fontSize: "11px",
              letterSpacing: "0.1em",
              textTransform: "uppercase",
              color: "color-mix(in srgb, var(--color-text) 50%, transparent)",
            }}
          >
            Progress
          </div>
          <div style={{ display: "flex", alignItems: "flex-end", gap: "8px", marginTop: "4px" }}>
            <span className="ovnum" style={{ fontSize: "52px", color: "var(--color-accent)" }}>
              {progress.current}
            </span>
            <span className="text-muted" style={{ fontSize: "13px", paddingBottom: "8px" }}>
              of {progress.total} chapters
            </span>
          </div>
        </>
      )}

      {completionReason && (
        <>
          <hr className="hr" style={{ margin: "20px 0", height: "1px" }} />
          <div
            style={{
              fontSize: "11px",
              letterSpacing: "0.1em",
              textTransform: "uppercase",
              color: "color-mix(in srgb, var(--color-text) 50%, transparent)",
            }}
          >
            The story has ended
          </div>
          <p style={{ margin: "8px 0 0", fontSize: "15px", lineHeight: 1.5 }} role="status">
            {REASON_LABELS[completionReason.type] || "The story ended"}
            {completionReason.detail ? ` — ${completionReason.detail}` : ""}
          </p>
        </>
      )}
    </div>
  );
}

export default StatusPanel;
