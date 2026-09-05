/**
 * 2-3 clickable alternative actions that submit directly (specs/designs/03-play.html).
 * Always rendered alongside the free-text input, never a replacement for it.
 */
export function SuggestedActions({ actions, onSelect, disabled }) {
  if (!actions || actions.length === 0) return null;

  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", marginBottom: "14px" }}>
      <span
        style={{
          fontSize: "11px",
          letterSpacing: "0.1em",
          textTransform: "uppercase",
          color: "color-mix(in srgb, var(--color-text) 45%, transparent)",
          alignSelf: "center",
          marginRight: "4px",
        }}
      >
        Try
      </span>
      {actions.map((action) => (
        <button
          key={action}
          type="button"
          className="btn btn-secondary"
          style={{ fontSize: "13px", padding: "8px 12px" }}
          onClick={() => onSelect(action)}
          disabled={disabled}
        >
          {action}
        </button>
      ))}
    </div>
  );
}

export default SuggestedActions;
