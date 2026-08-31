/**
 * Tab 01 — name & cover (FR-009). A required story name and an optional cover image
 * uploaded from the administrator's device; the selected file is held locally (not
 * localStorage — File objects don't survive JSON serialization) until Save uploads it to
 * blob storage. Both fields are bound directly to the wizard's central, localStorage-backed
 * field state (FR-010) via `onChange`.
 */
export function StepNameCover({ fields, onChange, pendingCoverImageFile, onCoverImageFileSelected }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      <div className="field">
        <label htmlFor="story-name">Story name</label>
        <input
          id="story-name"
          className="input"
          value={fields.name}
          onChange={(event) => onChange({ name: event.target.value })}
        />
      </div>
      <div className="field">
        <label htmlFor="story-cover">Cover image (optional)</label>
        <input
          id="story-cover"
          className="input"
          type="file"
          accept="image/*"
          onChange={(event) => onCoverImageFileSelected(event.target.files?.[0] ?? null)}
        />
        {pendingCoverImageFile ? (
          <p className="text-muted" style={{ fontSize: "13px", marginTop: "8px" }}>
            Selected &ldquo;{pendingCoverImageFile.name}&rdquo; — uploads when you Save.
          </p>
        ) : (
          fields.coverImageUrl && (
            <img
              src={fields.coverImageUrl}
              alt="Current cover"
              style={{ maxWidth: "220px", filter: "grayscale(1)", marginTop: "8px" }}
            />
          )
        )}
      </div>
    </div>
  );
}

export default StepNameCover;
