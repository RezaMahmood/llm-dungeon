import SavedGameRow from "./SavedGameRow.jsx";

/**
 * "Stories in progress" section (specs/designs/02-story-select.html) rendered above
 * "01 — Choose an adventure" on the stories screen (`/game`, research.md Decision 9).
 * Renders the FR-002 empty-state message rather than an empty box when the player has
 * nothing to continue.
 */
export function StoriesInProgress({ sessions, loading, error, onResume }) {
  return (
    <section aria-labelledby="stories-in-progress-heading">
      <div style={{ display: "flex", alignItems: "flex-end", gap: "16px" }}>
        <div className="ovnum" style={{ fontSize: "56px", color: "var(--color-accent)" }}>
          2
        </div>
        <div style={{ paddingBottom: "4px" }}>
          <div
            style={{
              fontSize: "12px",
              letterSpacing: "0.1em",
              textTransform: "uppercase",
              color: "var(--color-accent-700)",
            }}
          >
            Keep going
          </div>
          <h2 id="stories-in-progress-heading" style={{ margin: "4px 0 0", fontSize: "16px" }}>
            Stories in progress
          </h2>
        </div>
      </div>
      <hr className="hr" style={{ margin: "16px 0 0" }} />

      {loading ? (
        <p className="text-muted" style={{ margin: "20px 0" }}>
          Loading your stories…
        </p>
      ) : error ? (
        <p role="alert" className="text-muted" style={{ margin: "20px 0" }}>
          Couldn&rsquo;t load your stories in progress. Please try again.
        </p>
      ) : sessions.length === 0 ? (
        <div style={{ padding: "32px 20px", border: "1px solid var(--color-divider)", textAlign: "center", marginTop: "2px" }}>
          <p className="text-muted" style={{ margin: 0 }}>
            Nothing to continue yet — start an adventure below.
          </p>
        </div>
      ) : (
        sessions.map((session, index) => (
          <SavedGameRow key={session.sessionId} session={session} ordinal={String(index + 1).padStart(2, "0")} onResume={onResume} />
        ))
      )}
      {/* Visible divider closing the section (Constitution "Screen contracts"). */}
      <hr className="hr" style={{ margin: "24px 0 0" }} />
    </section>
  );
}

export default StoriesInProgress;
