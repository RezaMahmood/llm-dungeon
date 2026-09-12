import { useMsal } from "@azure/msal-react";
import { memo, useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import StoryConfigUpload from "../components/Admin/StoryConfigUpload.jsx";
import StoryDeleteAction from "../components/Admin/StoryDeleteAction.jsx";
import StoryPublishActions from "../components/Admin/StoryPublishActions.jsx";
import { loginRequest } from "../services/msalConfig.js";
import { listStories } from "../services/storyDraftService.js";

// Formatted for the Status tag's hover title (026-token-usage FR-006) — undefined/invalid
// input renders no title at all, never a fabricated date.
function formatLastPublished(iso) {
  if (!iso) return undefined;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return undefined;
  return date.toLocaleString();
}

// Memoized: `handleStoryChange`/`handleStoryDeleted` update `stories` by mapping/filtering
// in place, so a story untouched by a publish/delete action keeps its old object reference
// — this lets an edit to one row skip re-rendering every other row in the table.
const StoryRow = memo(function StoryRow({ story, getToken, onStoryChange, onDeleted }) {
  const lastPublishedTitle = formatLastPublished(story.lastPublishedAt);

  return (
    <tr>
      <td>{story.name || "Untitled story"}</td>
      <td>
        {/* Status pairs color with text, never color alone (Accessibility). The
            last-published date moved off this line (research.md Decision 8) and onto a
            native `title` attribute instead, freeing room for the Tokens column. */}
        <span
          className={story.published ? "tag tag-accent" : "tag tag-neutral"}
          title={lastPublishedTitle}
        >
          {story.published ? "Published" : "Unpublished"}
        </span>
      </td>
      <td>{(story.totalTokens || 0).toLocaleString()}</td>
      <td>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-2)", alignItems: "center" }}>
          <Link to={`/admin/stories/${story.id}`} className="btn btn-secondary">
            View
          </Link>
          <Link to={`/admin/stories/${story.id}/edit`} className="btn btn-secondary">
            Edit
          </Link>
          <StoryPublishActions story={story} token={getToken} onStoryChange={onStoryChange} hideStatusLine />
          <StoryDeleteAction story={story} token={getToken} onDeleted={onDeleted} />
        </div>
      </td>
    </tr>
  );
});

/**
 * The admin "Stories" destination — every story with its published status, a View
 * affordance into the read-only configuration viewer, an Edit affordance into the wizard,
 * publish/unpublish from the row, and the configuration upload entry point (FR-001,
 * FR-005, FR-011, SC-001, SC-007).
 */
export function AdminPage() {
  const { instance, accounts: msalAccounts } = useMsal();
  const account = msalAccounts[0];
  const accountKey = account?.homeAccountId ?? account?.username ?? null;

  const [stories, setStories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Resolved lazily, per call, rather than cached in state — so a click made before the
  // first `refresh()` settles (or long after the token would have expired) always sends a
  // fresh token instead of racing a `null` one.
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
      const data = await listStories(token);
      setStories(data.stories || []);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [getToken]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const handleStoryChange = useCallback((updatedStory) => {
    setStories((current) => current.map((story) => (story.id === updatedStory.id ? updatedStory : story)));
  }, []);

  const handleStoryDeleted = useCallback((deletedStoryId) => {
    setStories((current) => current.filter((story) => story.id !== deletedStoryId));
  }, []);

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

      <StoryConfigUpload token={getToken} onImported={refresh} />
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
              <th scope="col">Tokens</th>
              <th scope="col">Actions</th>
            </tr>
          </thead>
          <tbody>
            {stories.map((story) => (
              <StoryRow
                key={story.id}
                story={story}
                getToken={getToken}
                onStoryChange={handleStoryChange}
                onDeleted={handleStoryDeleted}
              />
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default AdminPage;
