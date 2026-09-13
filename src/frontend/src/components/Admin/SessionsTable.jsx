import { memo } from "react";

/**
 * The Sessions (admin) table — every gameplay session in the instance, player and admin
 * test-play alike, with a per-row delete (specs/designs/08-admin-sessions-spec.md §5,
 * 031-sessions-admin-design-spec FR-003–FR-005, FR-017).
 */

// The server substitutes this label for a story that no longer exists
// (SessionOverviewService.DELETED_STORY_LABEL). It is contract, not incidental copy: the
// client depends on it both to render the italic treatment here and to exclude the row
// from the heading's story count (data-model.md).
export const DELETED_STORY_LABEL = "(deleted story)";

function TrashIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      style={{ flex: "none" }}
      aria-hidden="true"
    >
      <path d="M3 6h18" />
      <path d="M8 6V4a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v2" />
      <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
    </svg>
  );
}

// Memoized with a stable `onSelectDelete` so opening the confirm dialog for one row
// doesn't re-render every other row (the same reason AccountRow is memoized).
const SessionRow = memo(function SessionRow({ session, onSelectDelete }) {
  const storyDeleted = session.storyName === DELETED_STORY_LABEL;

  return (
    <tr>
      <td>
        {storyDeleted ? (
          <span className="sessions-deleted-story">{DELETED_STORY_LABEL}</span>
        ) : (
          session.storyName
        )}
      </td>
      <td className="sessions-id-cell text-muted">{session.sessionId}</td>
      <td className="sessions-tokens-cell">{(session.totalTokens || 0).toLocaleString("en-GB")}</td>
      <td className="sessions-account-cell text-muted">{session.email}</td>
      <td className="sessions-actions-cell">
        <button
          type="button"
          className="btn btn-ghost"
          // The icon is decorative, so the label carries the name — and it names the
          // session, so a screen-reader user picking from a column of "Delete" buttons
          // can tell the rows apart.
          aria-label={`Delete session ${session.sessionId}`}
          style={{ padding: "6px 10px", fontSize: "12px", gap: "6px", whiteSpace: "nowrap" }}
          onClick={() => onSelectDelete(session)}
        >
          <TrashIcon />
          Delete
        </button>
      </td>
    </tr>
  );
});

export function SessionsTable({ sessions = [], onSelectDelete }) {
  return (
    <table className="table" style={{ marginTop: "10px" }}>
      <thead>
        <tr>
          <th scope="col">Story</th>
          <th scope="col">Session ID</th>
          <th scope="col" className="sessions-tokens-cell">
            Total tokens
          </th>
          <th scope="col">Account</th>
          {/* The actions column has no header text, as in the canonical mockup and in
              AccountList's equivalent — each row's button carries its own name. */}
          <th scope="col" className="sessions-actions-cell"></th>
        </tr>
      </thead>
      <tbody>
        {sessions.map((session) => (
          <SessionRow key={session.sessionId} session={session} onSelectDelete={onSelectDelete} />
        ))}
      </tbody>
    </table>
  );
}

export default SessionsTable;
