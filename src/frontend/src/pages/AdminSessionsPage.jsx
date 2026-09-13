import { useMsal } from "@azure/msal-react";
import { useCallback, useState } from "react";

import "../components/Admin/AdminSessions.css";
import SessionDeleteDialog from "../components/Admin/SessionDeleteDialog.jsx";
import SessionsTable, { DELETED_STORY_LABEL } from "../components/Admin/SessionsTable.jsx";
import { usePublishRefresh } from "../context/RefreshContext.jsx";
import { useRefreshable } from "../hooks/useRefreshable.js";
import { loginRequest } from "../services/msalConfig.js";
import { deleteSession, listSessions } from "../services/sessionService.js";

/**
 * The admin "Sessions" destination — every gameplay session in the instance, real player
 * and admin test-play alike, each row showing its story, session identifier, cumulative
 * token total and owning account, with a per-row delete behind a confirmation
 * (031-sessions-admin-design-spec; supersedes 026-token-usage FR-016's read-only rule).
 * Matches specs/designs/08-admin-sessions.html / 08-admin-sessions-spec.md.
 */

// FR-002: both halves singularise independently, and a story that has been deleted is not
// counted (08-admin-sessions-spec.md §4).
export function sessionsHeading(sessions) {
  if (sessions.length === 0) return "No sessions";
  const storyCount = new Set(
    sessions.map((session) => session.storyName).filter((name) => name !== DELETED_STORY_LABEL),
  ).size;
  const sessionPart = `${sessions.length} ${sessions.length === 1 ? "session" : "sessions"}`;
  const storyPart = `${storyCount} ${storyCount === 1 ? "story" : "stories"}`;
  return `${sessionPart} across ${storyPart}`;
}

export function AdminSessionsPage() {
  const { instance, accounts: msalAccounts } = useMsal();
  const account = msalAccounts[0];
  const accountKey = account?.homeAccountId ?? account?.username ?? null;

  const [token, setToken] = useState(null);
  const [pending, setPending] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [notice, setNotice] = useState(null);

  const fetchSessions = useCallback(async () => {
    const tokenResponse = await instance.acquireTokenSilent({ ...loginRequest, account });
    setToken(tokenResponse.accessToken);
    const data = await listSessions(tokenResponse.accessToken);
    return data.sessions || [];
    // eslint-disable-next-line react-hooks/exhaustive-deps -- accountKey is the stable dependency
  }, [instance, accountKey]);

  const { data, loading, error, refresh } = useRefreshable(fetchSessions);
  usePublishRefresh({ refresh, loading });

  // Rows deleted in this session's view, kept out of the table without a refetch — the
  // same pattern HomePage uses for a player deleting their own saved game. Harmless once a
  // real refresh lands, since the server has already stopped returning them by then.
  const [deletedIds, setDeletedIds] = useState(() => new Set());

  const sessions = (data || []).filter((session) => !deletedIds.has(session.sessionId));

  const handleSelectDelete = useCallback((session) => {
    setNotice(null);
    setPending(session);
  }, []);

  // FR-014: the row leaves the table only on the server's word. A failure keeps it, and
  // the one case that removes it without a successful delete is a 404 — which is still
  // the server confirming the session is gone, just not by this call (FR-015).
  const handleConfirmDelete = async () => {
    setDeleting(true);
    try {
      await deleteSession(token, pending.sessionId);
      setDeletedIds((prev) => new Set(prev).add(pending.sessionId));
      setPending(null);
    } catch (err) {
      if (err.response?.status === 404) {
        setDeletedIds((prev) => new Set(prev).add(pending.sessionId));
        setPending(null);
        setNotice("That session had already been removed.");
      } else {
        setPending(null);
        setNotice("Couldn’t delete that session. It’s still here — please try again.");
      }
    } finally {
      setDeleting(false);
    }
  };

  // Never states a count before the first successful load: `data` is null until then and
  // stays null through a failed first load, so deriving a heading from an empty array
  // would claim "No sessions" while still loading (the same trap AdminAccountsPage's
  // heading avoids).
  const heading = data === null ? "Sessions" : sessionsHeading(sessions);

  return (
    <div className="sessions-shell">
      <div className="sessions-header">
        <div className="sessions-kicker">Sessions</div>
        <h2 className="sessions-heading">{heading}</h2>
        <hr className="hr" style={{ margin: "20px 0 32px" }} />
      </div>

      <div className="sessions-scroll">
        {error && (
          <p role="alert" className="text-muted">
            Couldn&rsquo;t refresh the session list. Showing the last loaded results.
          </p>
        )}
        {notice && (
          <p role="alert" className="text-muted">
            {notice}
          </p>
        )}

        {loading && data === null ? (
          <p className="text-muted">Loading sessions…</p>
        ) : sessions.length === 0 ? (
          <p className="sessions-empty text-muted">
            No sessions yet. They appear here as soon as someone starts a story.
          </p>
        ) : (
          <>
            <div className="sessions-table-label">All sessions</div>
            <SessionsTable sessions={sessions} onSelectDelete={handleSelectDelete} />
            <p className="sessions-caption text-muted">
              Deleting a session permanently removes the player&rsquo;s saved progress and its
              transcript. The tokens it spent stay counted in the usage telemetry.
            </p>
          </>
        )}
      </div>

      {pending && (
        <SessionDeleteDialog
          session={pending}
          working={deleting}
          onCancel={() => setPending(null)}
          onConfirm={handleConfirmDelete}
        />
      )}
    </div>
  );
}

export default AdminSessionsPage;
