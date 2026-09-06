import { Link, useNavigate } from "react-router-dom";

import { usePlayTitle } from "../../context/PlayTitleContext.jsx";

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
 * `storyTitle`/`onPauseExit` come either from props or from whatever the mounted
 * page published via `PlayTitleContext` (`008-core-gameplay`'s play surface does
 * the latter). While a page has published an exit handler there is an active play
 * session, so *every* way out of this bar — the exit action and the brand mark
 * alike — has to run through it: FR-016/SC-013 allow no path that leaves an active
 * session without the pause confirmation. With nothing published (e.g. the setup
 * screen at /game) both fall back to returning to story select directly.
 */
export function TitleBar({ storyTitle = "", onSaveCheckpoint, onPauseExit }) {
  const navigate = useNavigate();
  const published = usePlayTitle();
  const title = storyTitle || published?.storyTitle || "";
  const confirmExit = onPauseExit ?? published?.onPauseExit;
  const handlePauseExit = confirmExit ?? (() => navigate("/menu"));

  const brandStyle = {
    fontFamily: "var(--font-heading)",
    fontWeight: "var(--font-heading-weight)",
    fontSize: "15px",
    textDecoration: "none",
    color: "var(--color-accent-700)",
    flex: "none",
  };

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
      {confirmExit ? (
        <button
          type="button"
          onClick={confirmExit}
          style={{ ...brandStyle, background: "none", border: 0, padding: 0, cursor: "pointer" }}
        >
          Lantern
        </button>
      ) : (
        <Link to="/menu" style={brandStyle}>
          Lantern
        </Link>
      )}
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
        {title}
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
