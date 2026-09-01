/**
 * Step 3: choose a character type from the selected adventure's set (FR-003, FR-003a).
 * A single type is still shown as an explicit radio choice, never auto-selected (edge case).
 */
export function CharacterTypeStep({ characterTypes, loading, error, selectedName, onSelect }) {
  if (loading) {
    return <p className="text-muted">Loading character types…</p>;
  }

  if (error) {
    return (
      <p role="alert" className="text-muted">
        Couldn&rsquo;t load character types. Please try again.
      </p>
    );
  }

  return (
    <div
      role="radiogroup"
      aria-label="Character type"
      style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "12px" }}
    >
      {(characterTypes || []).map((type) => (
        <label
          key={type.name}
          className="card"
          style={{ cursor: "pointer", padding: "16px", gap: "8px", border: "1px solid var(--color-divider)" }}
        >
          <span className="radio" style={{ fontSize: "14px", fontWeight: 600 }}>
            <input
              type="radio"
              name="character-type"
              checked={type.name === selectedName}
              onChange={() => onSelect(type.name)}
            />
            <span className="dot"></span>
            {type.name}
          </span>
          {type.description && (
            <p className="card-body" style={{ margin: "0 0 0 24px" }}>
              {type.description}
            </p>
          )}
        </label>
      ))}
    </div>
  );
}

export default CharacterTypeStep;
