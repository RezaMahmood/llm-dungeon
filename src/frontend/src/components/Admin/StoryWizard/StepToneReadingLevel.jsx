import { useEffect, useState } from "react";

export function StepToneReadingLevel({ draft, onPatch }) {
  const [tone, setTone] = useState(draft.tone || "");
  const [readingLevel, setReadingLevel] = useState(draft.readingLevel || "");

  useEffect(() => setTone(draft.tone || ""), [draft.tone]);
  useEffect(() => setReadingLevel(draft.readingLevel || ""), [draft.readingLevel]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      <div className="field">
        <label htmlFor="story-tone">Tone</label>
        <input
          id="story-tone"
          className="input"
          value={tone}
          onChange={(event) => setTone(event.target.value)}
          onBlur={() => {
            if (tone !== (draft.tone || "")) onPatch({ tone });
          }}
        />
      </div>
      <div className="field">
        <label htmlFor="story-reading-level">Reading level</label>
        <input
          id="story-reading-level"
          className="input"
          value={readingLevel}
          onChange={(event) => setReadingLevel(event.target.value)}
          onBlur={() => {
            if (readingLevel !== (draft.readingLevel || "")) onPatch({ readingLevel });
          }}
        />
      </div>
    </div>
  );
}

export default StepToneReadingLevel;
