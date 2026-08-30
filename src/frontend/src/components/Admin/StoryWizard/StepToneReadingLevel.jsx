import { useEffect, useState } from "react";

export function StepToneReadingLevel({ draft, onPatch }) {
  const [tone, setTone] = useState(draft.tone || "");
  const [readingLevel, setReadingLevel] = useState(draft.readingLevel || "");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => setTone(draft.tone || ""), [draft.tone]);
  useEffect(() => setReadingLevel(draft.readingLevel || ""), [draft.readingLevel]);

  const dirty = tone !== (draft.tone || "") || readingLevel !== (draft.readingLevel || "");

  const handleSave = async () => {
    setSaving(true);
    try {
      await onPatch({ tone, readingLevel });
      setSaved(true);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      <div className="field">
        <label htmlFor="story-tone">Tone</label>
        <input
          id="story-tone"
          className="input"
          value={tone}
          onChange={(event) => {
            setTone(event.target.value);
            setSaved(false);
          }}
        />
      </div>
      <div className="field">
        <label htmlFor="story-reading-level">Reading level</label>
        <input
          id="story-reading-level"
          className="input"
          value={readingLevel}
          onChange={(event) => {
            setReadingLevel(event.target.value);
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

export default StepToneReadingLevel;
