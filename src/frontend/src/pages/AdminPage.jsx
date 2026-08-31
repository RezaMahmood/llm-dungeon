import { useMsal } from "@azure/msal-react";
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { loginRequest } from "../services/msalConfig.js";
import { listStories } from "../services/storyDraftService.js";

/**
 * The admin "Stories" destination — a minimal, read-only list of the stories
 * that exist, so "Stories" and "New story" are distinct places to go
 * (FR-002, FR-013, SC-007).
 *
 * Editing, publishing and deleting stories are deliberately not here; those
 * belong to 005-story-publishing / 012-story-editing-and-review.
 */
export function AdminPage() {
  const { instance, accounts: msalAccounts } = useMsal();
  const account = msalAccounts[0];
  const accountKey = account?.homeAccountId ?? account?.username ?? null;

  const [stories, setStories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const tokenResponse = await instance.acquireTokenSilent({ ...loginRequest, account });
      const data = await listStories(tokenResponse.accessToken);
      setStories(data.stories || []);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- accountKey is the stable dependency
  }, [instance, accountKey]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return (
    <div style={{ maxWidth: "1020px", padding: "var(--space-6) var(--space-4) 64px" }}>
      <div
        style={{
          display: "flex",
          alignItems: "flex-end",
          justifyContent: "space-between",
          gap: "var(--space-4)",
        }}
      >
        <h1 style={{ margin: 0 }}>Stories</h1>
        <Link to="/admin/stories/new" className="btn btn-primary">
          New story
        </Link>
      </div>
      <hr className="hr" />

      {loading && <p className="text-muted">Loading stories…</p>}

      {!loading && error && (
        <div>
          <p role="alert">Something went wrong. Please try again.</p>
          <button type="button" className="btn btn-secondary" onClick={refresh}>
            Try again
          </button>
        </div>
      )}

      {!loading && !error && stories.length === 0 && (
        <p className="text-muted">
          No stories yet. Use “New story” to build the first one.
        </p>
      )}

      {!loading && !error && stories.length > 0 && (
        <table className="table">
          <thead>
            <tr>
              <th scope="col">Story</th>
              <th scope="col">Status</th>
            </tr>
          </thead>
          <tbody>
            {stories.map((story) => (
              <tr key={story.id}>
                <td>{story.name || "Untitled story"}</td>
                <td>
                  {/* Status pairs color with text, never color alone (Accessibility). */}
                  <span className={story.published ? "tag tag-accent" : "tag tag-neutral"}>
                    {story.published ? "Published" : "Draft"}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default AdminPage;
