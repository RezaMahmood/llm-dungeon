import { useEffect, useState } from "react";

export function StepSessionLength({ draft, onPatch }) {
  const [sessionLengthMinutes, setSessionLengthMinutes] = useState(draft.sessionLengthMinutes ?? "");
  const [chapters, setChapters] = useState(draft.chapters ?? "");

  useEffect(() => setSessionLengthMinutes(draft.sessionLengthMinutes ?? ""), [draft.sessionLengthMinutes]);
  useEffect(() => setChapters(draft.chapters ?? ""), [draft.chapters]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      <div className="field">
        <label htmlFor="session-length">Session length before a natural stopping point (minutes)</label>
        <input
          id="session-length"
          className="input"
          type="number"
          value={sessionLengthMinutes}
          onChange={(event) => setSessionLengthMinutes(event.target.value)}
          onBlur={() => {
            const next = sessionLengthMinutes ? Number(sessionLengthMinutes) : null;
            if (next !== (draft.sessionLengthMinutes ?? null)) onPatch({ sessionLengthMinutes: next });
          }}
        />
      </div>
      <div className="field">
        <label htmlFor="chapters">Chapters</label>
        <input
          id="chapters"
          className="input"
          type="number"
          value={chapters}
          onChange={(event) => setChapters(event.target.value)}
          onBlur={() => {
            const next = chapters ? Number(chapters) : null;
            if (next !== (draft.chapters ?? null)) onPatch({ chapters: next });
          }}
        />
      </div>
    </div>
  );
}

export default StepSessionLength;
