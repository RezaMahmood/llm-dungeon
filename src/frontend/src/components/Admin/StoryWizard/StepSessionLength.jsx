import { useEffect, useState } from "react";

export function StepSessionLength({ draft, onPatch }) {
  const [sessionLengthMinutes, setSessionLengthMinutes] = useState(draft.sessionLengthMinutes ?? "");
  const [chapters, setChapters] = useState(draft.chapters ?? "");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => setSessionLengthMinutes(draft.sessionLengthMinutes ?? ""), [draft.sessionLengthMinutes]);
  useEffect(() => setChapters(draft.chapters ?? ""), [draft.chapters]);

  const dirty =
    sessionLengthMinutes !== (draft.sessionLengthMinutes ?? "") || chapters !== (draft.chapters ?? "");

  const handleSave = async () => {
    setSaving(true);
    try {
      await onPatch({
        sessionLengthMinutes: sessionLengthMinutes ? Number(sessionLengthMinutes) : null,
        chapters: chapters ? Number(chapters) : null,
      });
      setSaved(true);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      <div className="field">
        <label htmlFor="session-length">Session length before a natural stopping point (minutes)</label>
        <input
          id="session-length"
          className="input"
          type="number"
          value={sessionLengthMinutes}
          onChange={(event) => {
            setSessionLengthMinutes(event.target.value);
            setSaved(false);
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
          onChange={(event) => {
            setChapters(event.target.value);
            setSaved(false);
          }}
        />
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        <button type="button" className="btn btn-primary" onClick={handleSave} disabled={!dirty || saving}>
          {saving ? "Saving…" : "Save"}
        </button>
        {saved && !dirty && <span className="text-muted" style={{ fontSize: "13px" }}>Saved</span>}
      </div>
    </div>
  );
}

export default StepSessionLength;
