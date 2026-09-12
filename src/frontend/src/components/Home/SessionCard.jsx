import "./Home.css";

/** Same formatting `GameSetup/SavedGameRow.jsx` used for the pre-Home in-progress list —
 * preformats a "Last played {date}" phrase, or `null` when there is nothing to show. */
function formatLastPlayed(iso) {
  if (!iso) return null;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return null;
  return `Last played ${date.toLocaleDateString(undefined, { month: "short", day: "numeric" })}`;
}

/** One "In progress" card (specs/designs/07-home-spec.md §5.2, FR-003). Carries the
 * unavailable-story state `SavedGameRow.jsx` provided before Home (FR-018): a story that
 * was unpublished or deleted while a session was open is marked, not hidden, and Resume
 * is disabled. `deleteAction`, when supplied, renders beside Resume (US3). */
export function SessionCard({ session, onResume, deleteAction }) {
  const { adventureName, locationLabel, progress, lastInteractionAt } = session;
  const available = session.available !== false;

  const metaParts = [
    progress ? `Chapter ${progress.current}` : null,
    formatLastPlayed(lastInteractionAt),
    locationLabel,
  ].filter(Boolean);

  return (
    <a
      className={`home-pcard home-rowhov${available ? "" : " home-pcard-unavailable"}`}
      href="#resume"
      style={available ? undefined : { opacity: 0.5 }}
      onClick={(event) => {
        event.preventDefault();
        if (available) onResume(session);
      }}
    >
      <div className="home-pcard-title" style={{ width: "100%" }}>
        {adventureName}
      </div>
      {metaParts.length > 0 && (
        <div className="text-muted" style={{ fontSize: "12px", marginTop: "4px", width: "100%" }}>
          {metaParts.join(" · ")}
        </div>
      )}
      {!available && (
        <span className="tag tag-neutral text-muted" style={{ fontSize: "11px", marginTop: "4px" }}>
          Unavailable
        </span>
      )}
      {progress && (
        <div className="home-pcard-bars">
          {Array.from({ length: progress.total }, (_, index) => (
            <span key={index} className={index < progress.current ? "filled" : ""} />
          ))}
        </div>
      )}
      <span className="home-pcard-actions">
        {available ? (
          <span className="btn btn-secondary" style={{ padding: "9px 14px", fontSize: "13px" }}>
            Resume
          </span>
        ) : (
          <span className="btn btn-secondary" aria-disabled="true" style={{ padding: "9px 14px", fontSize: "13px" }}>
            Unavailable
          </span>
        )}
        {deleteAction}
      </span>
    </a>
  );
}

export default SessionCard;
