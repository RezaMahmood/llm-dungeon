/**
 * Scrolling narrative history for the play surface (specs/designs/03-play.html,
 * 008-core-gameplay). Renders every turn so far: the narrative text, and — when
 * present — the player's own input for that turn, oldest first.
 */
export function StoryPane({ turns }) {
  return (
    <div
      className="storyscroll"
      style={{ flex: 1, overflowY: "auto", padding: "32px 40px 20px" }}
      aria-live="polite"
    >
      <div style={{ maxWidth: "64ch" }}>
        {turns.map((turn) => (
          <div key={turn.turnNumber}>
            {turn.playerInput != null && (
              <div style={{ marginBottom: "22px" }}>
                <div
                  style={{
                    fontSize: "11px",
                    letterSpacing: "0.1em",
                    textTransform: "uppercase",
                    color: "color-mix(in srgb, var(--color-text) 45%, transparent)",
                    marginBottom: "6px",
                  }}
                >
                  You
                </div>
                <p style={{ margin: 0, fontSize: "19px", lineHeight: 1.65 }}>{turn.playerInput}</p>
              </div>
            )}
            <div style={{ marginBottom: "22px" }}>
              <div
                style={{
                  fontSize: "11px",
                  letterSpacing: "0.1em",
                  textTransform: "uppercase",
                  color: "color-mix(in srgb, var(--color-text) 45%, transparent)",
                  marginBottom: "6px",
                }}
              >
                The story
              </div>
              <p style={{ margin: 0, fontSize: "19px", lineHeight: 1.65 }}>{turn.narrativeText}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default StoryPane;
