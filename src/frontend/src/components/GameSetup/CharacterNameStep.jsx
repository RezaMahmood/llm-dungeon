export const MAX_CHARACTER_NAME_LENGTH = 50;

/**
 * Step 2: name the character (FR-002). Only rendered once an adventure is selected
 * (FR-003a — enforced by the parent, GamePage). Client-side hint mirrors the server rule
 * in start.py; the server remains the authority (Constitution Principle II).
 */
export function CharacterNameStep({ value, onChange, error }) {
  return (
    <div className="field" style={{ maxWidth: "420px" }}>
      <label htmlFor="character-name">Character name</label>
      <input
        id="character-name"
        className="input"
        type="text"
        maxLength={MAX_CHARACTER_NAME_LENGTH}
        placeholder="e.g. Wren"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
      {error && (
        <p role="alert" style={{ fontSize: "12px", color: "var(--color-accent-700)", margin: "6px 0 0" }}>
          {error}
        </p>
      )}
    </div>
  );
}

export default CharacterNameStep;
