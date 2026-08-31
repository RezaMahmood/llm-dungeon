/** Tab 04 — session length. Unchanged by the Session 2026-08-30 redesign (spec.md
 * Clarifications) other than binding directly to the wizard's central field state. */
export function StepSessionLength({ fields, onChange }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      <div className="field">
        <label htmlFor="session-length">Session length before a natural stopping point (minutes)</label>
        <input
          id="session-length"
          className="input"
          type="number"
          value={fields.sessionLengthMinutes}
          onChange={(event) => onChange({ sessionLengthMinutes: event.target.value })}
        />
      </div>
      <div className="field">
        <label htmlFor="chapters">Chapters</label>
        <input
          id="chapters"
          className="input"
          type="number"
          value={fields.chapters}
          onChange={(event) => onChange({ chapters: event.target.value })}
        />
      </div>
    </div>
  );
}

export default StepSessionLength;
