/**
 * In-app refresh control (FR-001–FR-004). Markup mirrors
 * `specs/designs/03-play.html`'s title-bar control exactly — see
 * contracts/refresh-control.md.
 */
export function RefreshButton({ onClick, loading }) {
  return (
    <button
      className="btn btn-ghost"
      type="button"
      title="Refresh"
      aria-label="Refresh"
      disabled={loading}
      onClick={onClick}
      style={{ gap: 8, padding: "8px 12px", fontSize: 13 }}
    >
      <svg
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        style={{ flex: "none" }}
      >
        <path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8" />
        <path d="M21 3v5h-5" />
        <path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16" />
        <path d="M8 16H3v5" />
      </svg>
      {loading ? "Refreshing…" : "Refresh"}
    </button>
  );
}

export default RefreshButton;
