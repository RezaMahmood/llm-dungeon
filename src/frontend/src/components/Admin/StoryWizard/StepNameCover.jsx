import { useEffect, useState } from "react";

export function StepNameCover({ draft, onPatch }) {
  const [name, setName] = useState(draft.name || "");
  const [coverImageUrl, setCoverImageUrl] = useState(draft.coverImageUrl || "");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => setName(draft.name || ""), [draft.name]);
  useEffect(() => setCoverImageUrl(draft.coverImageUrl || ""), [draft.coverImageUrl]);

  const dirty = name !== (draft.name || "") || coverImageUrl !== (draft.coverImageUrl || "");

  const handleSave = async () => {
    setSaving(true);
    try {
      await onPatch({ name, coverImageUrl });
      setSaved(true);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      <div className="field">
        <label htmlFor="story-name">Story name</label>
        <input
          id="story-name"
          className="input"
          value={name}
          onChange={(event) => {
            setName(event.target.value);
            setSaved(false);
          }}
        />
      </div>
      <div className="field">
        <label htmlFor="story-cover">Cover image URL</label>
        <input
          id="story-cover"
          className="input"
          value={coverImageUrl}
          onChange={(event) => {
            setCoverImageUrl(event.target.value);
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

export default StepNameCover;
