import { useMsal } from "@azure/msal-react";
import { useCallback, useEffect, useState } from "react";

import { loginRequest } from "../services/msalConfig.js";
import { listSessions } from "../services/sessionService.js";

/**
 * The admin "Sessions" destination — a read-only list of every gameplay session, real
 * player and admin test-play alike, each row showing its story, a session identifier,
 * its cumulative token total, and the email of whoever played it (026-token-usage
 * FR-015, FR-016, FR-018). No create/edit/delete affordance anywhere on this page.
 */
export function AdminSessionsPage() {
  const { instance, accounts: msalAccounts } = useMsal();
  const account = msalAccounts[0];
  const accountKey = account?.homeAccountId ?? account?.username ?? null;

  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const getToken = useCallback(async () => {
    const tokenResponse = await instance.acquireTokenSilent({ ...loginRequest, account });
    return tokenResponse.accessToken;
    // eslint-disable-next-line react-hooks/exhaustive-deps -- accountKey is the stable dependency
  }, [instance, accountKey]);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const token = await getToken();
      const data = await listSessions(token);
      setSessions(data.sessions || []);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [getToken]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return (
    <div style={{ maxWidth: "1020px", padding: "var(--space-6) var(--space-4) 64px" }}>
      <h1 style={{ margin: 0 }}>Sessions</h1>
      <hr className="hr" />

      {loading && <p className="text-muted">Loading sessions…</p>}

      {!loading && error && (
        <div>
          <p role="alert">Something went wrong. Please try again.</p>
          <button type="button" className="btn btn-secondary" onClick={refresh}>
            Try again
          </button>
        </div>
      )}

      {!loading && !error && sessions.length === 0 && (
        <p className="text-muted">No gameplay sessions yet.</p>
      )}

      {!loading && !error && sessions.length > 0 && (
        <table className="table">
          <thead>
            <tr>
              <th scope="col">Story</th>
              <th scope="col">Session ID</th>
              <th scope="col">Total Tokens</th>
              <th scope="col">Email</th>
            </tr>
          </thead>
          <tbody>
            {sessions.map((session) => (
              <tr key={session.sessionId}>
                <td>{session.storyName}</td>
                <td>{session.sessionId}</td>
                <td>{(session.totalTokens || 0).toLocaleString()}</td>
                <td>{session.email}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default AdminSessionsPage;
