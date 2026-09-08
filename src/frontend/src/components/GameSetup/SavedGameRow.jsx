/**
 * One row of the "stories in progress" list (specs/designs/02-story-select.html):
 * ordinal, adventure title, "chapter · last played · location" meta line, progress
 * bars, a saved indicator, and the Resume action (009-save-and-continue, FR-001).
 */
function formatLastPlayed(iso) {
  if (!iso) return null;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return null;
  return `Last played ${date.toLocaleDateString(undefined, { month: "short", day: "numeric" })}`;
}

export function SavedGameRow({ session, ordinal, onResume }) {
  const { adventureName, characterName, locationLabel, progress, isActiveForPlayer, checkpointCount } = session;
  // Absent `available` (pre-025 fixture data / a session whose story was never
  // unpublished) defaults to available, matching the backend's own default (FR-009,
  // FR-011).
  const available = session.available !== false;

  const metaParts = [
    progress ? `Chapter ${progress.current}` : null,
    formatLastPlayed(session.lastInteractionAt),
    locationLabel,
  ].filter(Boolean);

  return (
    <div
      className="rowhov"
      style={{
        display: "grid",
        gridTemplateColumns: "72px 1fr auto",
        gap: "24px",
        alignItems: "center",
        padding: "22px 12px",
        borderBottom: "1px solid var(--color-divider)",
        opacity: available ? 1 : 0.5,
      }}
    >
      <div className="ovnum" style={{ fontSize: "40px", color: "var(--color-accent)" }}>
        {ordinal}
      </div>
      <div>
        <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
          <span style={{ fontFamily: "var(--font-heading)", fontWeight: 800, fontSize: "20px" }}>
            {adventureName}
            {characterName ? ` — ${characterName}` : ""}
          </span>
          {isActiveForPlayer && (
            <span className="tag tag-neutral" style={{ fontSize: "11px" }}>
              Current game
            </span>
          )}
          {checkpointCount > 0 && (
            <span className="tag tag-neutral" style={{ fontSize: "11px" }}>
              Saved
            </span>
          )}
          {!available && (
            <span className="tag tag-neutral text-muted" style={{ fontSize: "11px" }}>
              Unavailable
            </span>
          )}
        </div>
        {metaParts.length > 0 && (
          <div className="text-muted" style={{ fontSize: "13px", marginTop: "6px" }}>
            {metaParts.join(" · ")}
          </div>
        )}
        {progress && (
          <div style={{ display: "flex", gap: "6px", marginTop: "12px" }}>
            {Array.from({ length: progress.total }, (_, index) => (
              <span
                key={index}
                style={{
                  height: "6px",
                  width: "48px",
                  background: index < progress.current ? "var(--color-accent)" : "var(--color-neutral-300)",
                }}
              />
            ))}
          </div>
        )}
      </div>
      {available ? (
        <button
          type="button"
          className={isActiveForPlayer ? "btn btn-primary" : "btn btn-secondary"}
          style={{ padding: "12px 18px" }}
          onClick={() => onResume(session)}
        >
          Resume
        </button>
      ) : (
        <button type="button" className="btn btn-secondary" style={{ padding: "12px 18px" }} disabled>
          Unavailable
        </button>
      )}
    </div>
  );
}

export default SavedGameRow;
