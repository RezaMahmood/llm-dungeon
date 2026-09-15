export const MIN_AVATAR_DESCRIPTION_LENGTH = 20;
export const MAX_AVATAR_DESCRIPTION_LENGTH = 500;

/**
 * Step 2: describe the player's own character (032-story-archetypes-player-avatar
 * FR-001, FR-002). Replaces the administrator-roster character-type picker — no list of
 * types is offered here or anywhere else in setup. Client-side length hint mirrors the
 * server rule in avatar_validation_service.py; the server remains the authority
 * (Constitution Principle II) and additionally judges story-relevance, which this
 * component cannot check client-side.
 */
export function AvatarDescriptionStep({ value, onChange, error, disabled }) {
  const trimmedLength = value.trim().length;

  return (
    <div className="field" style={{ maxWidth: "560px" }}>
      <label htmlFor="avatar-description">Describe your character</label>
      <textarea
        id="avatar-description"
        className="input"
        rows={4}
        maxLength={MAX_AVATAR_DESCRIPTION_LENGTH}
        placeholder="Who are they? What are they like? What can they do?"
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
      />
      <p style={{ fontSize: "12px", color: "var(--color-text-muted)", margin: "6px 0 0" }}>
        {trimmedLength}/{MAX_AVATAR_DESCRIPTION_LENGTH} characters (at least {MIN_AVATAR_DESCRIPTION_LENGTH})
      </p>
      {error && (
        <p role="alert" style={{ fontSize: "12px", color: "var(--color-accent-700)", margin: "6px 0 0" }}>
          {error}
        </p>
      )}
    </div>
  );
}

export default AvatarDescriptionStep;
