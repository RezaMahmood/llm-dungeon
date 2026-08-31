/** Tab 03 — tone & reading level. Unchanged by the Session 2026-08-30 redesign (spec.md
 * Clarifications) other than binding directly to the wizard's central field state. */
export function StepToneReadingLevel({ fields, onChange }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      <div className="field">
        <label htmlFor="story-tone">Tone</label>
        <input
          id="story-tone"
          className="input"
          value={fields.tone}
          onChange={(event) => onChange({ tone: event.target.value })}
        />
      </div>
      <div className="field">
        <label htmlFor="story-reading-level">Reading level</label>
        <input
          id="story-reading-level"
          className="input"
          value={fields.readingLevel}
          onChange={(event) => onChange({ readingLevel: event.target.value })}
        />
      </div>
    </div>
  );
}

export default StepToneReadingLevel;
