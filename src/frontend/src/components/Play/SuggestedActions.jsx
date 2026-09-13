import "./Play.css";

/**
 * 2-3 clickable alternative actions that submit directly (specs/designs/03-play.html).
 * Always rendered alongside the free-text input, never a replacement for it.
 */
export function SuggestedActions({ actions, onSelect, disabled }) {
  if (!actions || actions.length === 0) return null;

  return (
    <div className="play-try">
      <span className="play-label">Try</span>
      {actions.map((action) => (
        <button
          key={action}
          type="button"
          className="btn btn-secondary play-chip"
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
