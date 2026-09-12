import HomeColumn from "./HomeColumn.jsx";
import SessionCard from "./SessionCard.jsx";

/** Right column — "In progress" (specs/designs/07-home-spec.md §5.2, FR-003). The
 * zero-state message is §6 state 1 — no card, no button, just the explanation. */
export function InProgressList({ sessions, loading, error, onResume, renderDeleteAction }) {
  const heading = sessions.length === 0 ? "Nothing in progress" : "In progress";

  return (
    <HomeColumn
      as="aside"
      className="home-col home-col-side"
      kicker="Keep going"
      heading={heading}
      loading={loading}
      loadingMessage="Loading your stories…"
      error={error}
      errorMessage="Couldn't load your stories in progress. Please try again."
    >
      {sessions.length === 0 ? (
        <div style={{ padding: "28px 8px" }}>
          <p style={{ margin: 0, fontSize: "15px" }}>
            When you open a story it lands here, so you can pick it straight back up next time.
          </p>
        </div>
      ) : (
        sessions.map((session) => (
          <SessionCard
            key={session.sessionId}
            session={session}
            onResume={onResume}
            deleteAction={renderDeleteAction?.(session)}
          />
        ))
      )}
    </HomeColumn>
  );
}

export default InProgressList;
