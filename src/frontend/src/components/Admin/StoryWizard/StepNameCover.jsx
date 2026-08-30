import { useEffect, useState } from "react";

export function StepNameCover({ draft, onPatch }) {
  const [name, setName] = useState(draft.name || "");
  const [coverImageUrl, setCoverImageUrl] = useState(draft.coverImageUrl || "");

  useEffect(() => setName(draft.name || ""), [draft.name]);
  useEffect(() => setCoverImageUrl(draft.coverImageUrl || ""), [draft.coverImageUrl]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      <div className="field">
        <label htmlFor="story-name">Story name</label>
        <input
          id="story-name"
          className="input"
          value={name}
          onChange={(event) => setName(event.target.value)}
          onBlur={() => {
            if (name !== (draft.name || "")) onPatch({ name });
          }}
        />
      </div>
      <div className="field">
        <label htmlFor="story-cover">Cover image URL</label>
        <input
          id="story-cover"
          className="input"
          value={coverImageUrl}
          onChange={(event) => setCoverImageUrl(event.target.value)}
          onBlur={() => {
            if (coverImageUrl !== (draft.coverImageUrl || "")) onPatch({ coverImageUrl });
          }}
        />
      </div>
    </div>
  );
}

export default StepNameCover;
