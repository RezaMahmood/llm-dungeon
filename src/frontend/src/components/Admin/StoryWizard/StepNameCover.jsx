import { useEffect, useState } from "react";

export function StepNameCover({ draft, onPatch, onDirtyChange, fieldErrors = {} }) {
  const [name, setName] = useState(draft.name || "");
  const [coverImageUrl, setCoverImageUrl] = useState(draft.coverImageUrl || "");
  const [blurb, setBlurb] = useState(draft.blurb || "");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [saveFailed, setSaveFailed] = useState(false);

  useEffect(() => setName(draft.name || ""), [draft.name]);
  useEffect(() => setCoverImageUrl(draft.coverImageUrl || ""), [draft.coverImageUrl]);
  useEffect(() => setBlurb(draft.blurb || ""), [draft.blurb]);

  const dirty =
    name !== (draft.name || "") ||
    coverImageUrl !== (draft.coverImageUrl || "") ||
    blurb !== (draft.blurb || "");

  // Reports unsaved input up to the wizard page for FR-010's beforeunload warning.
  useEffect(() => {
    onDirtyChange?.(dirty);
    return () => onDirtyChange?.(false);
  }, [dirty, onDirtyChange]);

  // "Saved" must mean the server accepted the write. `onPatch` handles its own errors
  // rather than rejecting (the other steps fire it from blur handlers without awaiting
  // it), so it reports the outcome by returning false — confirming a save the server
  // refused is how an administrator silently loses a story name (#137).
  const handleSave = async () => {
    setSaving(true);
    setSaveFailed(false);
    try {
      const ok = await onPatch({ name, coverImageUrl, blurb });
      setSaved(ok !== false);
      setSaveFailed(ok === false);
    } finally {
      setSaving(false);
    }
  };

  const noteEdit = () => {
    setSaved(false);
    setSaveFailed(false);
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
            noteEdit();
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
            noteEdit();
          }}
        />
      </div>
      <div className="field">
        <label htmlFor="story-blurb">Blurb</label>
        <textarea
          id="story-blurb"
          className="input"
          value={blurb}
          onChange={(event) => {
            setBlurb(event.target.value);
            noteEdit();
          }}
        />
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        <button type="button" className="btn btn-primary" onClick={handleSave} disabled={!dirty || saving}>
          {saving ? "Saving…" : "Save"}
        </button>
        {saved && !dirty && <span className="text-muted" style={{ fontSize: "13px" }}>Saved</span>}
        {saveFailed && (
          <span role="alert" className="text-muted" style={{ fontSize: "13px" }}>
            {fieldErrors.name || "Could not save this — please try again."}
          </span>
        )}
      </div>
    </div>
  );
}

export default StepNameCover;
