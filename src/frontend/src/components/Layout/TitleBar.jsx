import { Link, useNavigate } from "react-router-dom";

/**
 * The compact title bar that replaces the full nav bar on the active
 * story-play screen (FR-006), so the story keeps the full reading height.
 * Structure follows `specs/designs/03-play.html`'s header.
 *
 * The Refresh control shown in that mockup belongs to
 * `019-spa-refresh-button` and is deliberately not built here; the trailing
 * cluster below is an ordinary flex row so it can be inserted later without
 * restructuring (plan.md Constitution Check, Principle XI).
 *
 * `onSaveCheckpoint`/`onPauseExit` may be supplied by the page once real
 * checkpoint/pause behavior exists (`008-core-gameplay`'s scope). Until then,
 * "Pause & exit" must still return the player to story select rather than
 * being a dead button — this feature's nav bar is the only wayfinding
 * mechanism now, so `onPauseExit` defaults to that return trip when the page
 * doesn't yet supply its own handler.
 */
export function TitleBar({ storyTitle = "", onSaveCheckpoint, onPauseExit }) {
  const navigate = useNavigate();
  const handlePauseExit = onPauseExit ?? (() => navigate("/menu"));

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "var(--space-4)",
        padding: "var(--space-3) var(--space-4)",
        borderBottom: "2px solid var(--color-divider)",
        flex: "none",
      }}
    >
      <Link
        to="/menu"
        style={{
          fontFamily: "var(--font-heading)",
          fontWeight: "var(--font-heading-weight)",
          fontSize: "15px",
          textDecoration: "none",
          color: "var(--color-accent-700)",
          flex: "none",
        }}
      >
        Lantern
      </Link>
      <span className="nav-divider" />
      <span
        className="truncate"
        style={{
          fontFamily: "var(--font-heading)",
          fontWeight: "var(--font-heading-weight)",
          fontSize: "17px",
          marginRight: "auto",
        }}
      >
        {storyTitle}
      </span>

      <span
        data-nav-slot="trailing-actions"
        style={{ display: "flex", alignItems: "center", gap: "var(--space-3)", flex: "none" }}
      >
        <button className="btn btn-secondary" type="button" onClick={onSaveCheckpoint}>
          Save a checkpoint
        </button>
        <button className="btn btn-primary" type="button" onClick={handlePauseExit}>
          Pause &amp; exit
        </button>
      </span>
    </div>
  );
}

export default TitleBar;
