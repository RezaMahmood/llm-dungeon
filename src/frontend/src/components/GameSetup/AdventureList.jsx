/**
 * Step 1: pick a published adventure (FR-001). Card grid matches
 * specs/designs/06-game-setup.html / 02-story-select.html's "Start something new" pattern.
 * Renders the FR-006 empty-state message when no adventures are published.
 */
export function AdventureList({ adventures, loading, error, selectedId, onSelect }) {
  if (loading) {
    return <p className="text-muted">Loading adventures…</p>;
  }

  if (error) {
    return (
      <p role="alert" className="text-muted">
        Couldn&rsquo;t load adventures. Please try again.
      </p>
    );
  }

  if (!adventures || adventures.length === 0) {
    return (
      <div style={{ padding: "32px 20px", border: "1px solid var(--color-divider)", textAlign: "center" }}>
        <p className="text-muted" style={{ margin: 0 }}>
          No adventures are published yet — check back soon.
        </p>
      </div>
    );
  }

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
        gap: "2px",
        background: "var(--color-divider)",
        borderBottom: "2px solid var(--color-divider)",
      }}
    >
      {adventures.map((adventure) => {
        const isSelected = adventure.id === selectedId;
        const kicker = [adventure.tone, adventure.sessionLengthMinutes ? `${adventure.sessionLengthMinutes} min` : null]
          .filter(Boolean)
          .join(" · ");
        return (
          <button
            key={adventure.id}
            type="button"
            className="card rowhov"
            aria-pressed={isSelected}
            onClick={() => onSelect(adventure.id)}
            style={{
              textAlign: "left",
              border: 0,
              cursor: "pointer",
              padding: "20px",
              gap: "8px",
              background: isSelected ? "var(--color-accent-100)" : "var(--color-bg)",
              font: "inherit",
              color: "inherit",
            }}
          >
            {kicker && <div className="card-kicker">{kicker}</div>}
            <div className="card-title" style={{ fontSize: "21px" }}>
              {adventure.name}
            </div>
            {adventure.readingLevel && <div className="card-meta">Reading level: {adventure.readingLevel}</div>}
          </button>
        );
      })}
    </div>
  );
}

export default AdventureList;
