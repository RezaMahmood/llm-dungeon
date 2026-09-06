import { useMsal } from "@azure/msal-react";
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { loginRequest } from "../services/msalConfig.js";
import { listStories } from "../services/storyDraftService.js";
import { usePublishToggle } from "../hooks/usePublishToggle.js";

/**
 * One story row's publish/unpublish action, sharing its call + FR-011
 * gate-message + FR-013 confirmation behavior with the wizard's
 * `StepPublish` via `usePublishToggle` (005-story-publishing-done Phase 5).
 */
function StoryRow({ story, getToken, onStoryChange }) {
  const {
    status,
    gateMessage,
    confirmingUnpublish,
    handlePublish,
    requestUnpublish,
    confirmUnpublish,
    cancelUnpublish,
  } = usePublishToggle(getToken, story, onStoryChange);

  const storyLabel = story.name || "this story";

  return (
    <tr>
      <td>{story.name || "Untitled story"}</td>
      <td>
        {/* Status pairs color with text, never color alone (Accessibility). */}
        <span className={story.published ? "tag tag-accent" : "tag tag-neutral"}>
          {story.published ? "Published" : "Draft"}
        </span>
      </td>
      <td>
        {!story.published && (
          <button
            type="button"
            className="btn btn-secondary"
            disabled={status === "working"}
            onClick={handlePublish}
          >
            {status === "working" ? "Publishing…" : "Publish"}
          </button>
        )}

        {story.published && (
          <button
            type="button"
            className="btn btn-secondary"
            disabled={status === "working"}
            onClick={requestUnpublish}
          >
            Unpublish
          </button>
        )}

        {gateMessage && (
          <div role="alert" className="text-muted" style={{ marginTop: "4px" }}>
            {gateMessage}
          </div>
        )}

        {status === "error" && (
          <div role="alert" className="text-muted" style={{ marginTop: "4px" }}>
            Could not update this story's published state. Please try again.
          </div>
        )}

        {confirmingUnpublish && (
          <div className="dialog-backdrop">
            <div
              className="dialog"
              role="dialog"
              aria-modal="true"
              aria-labelledby={`unpublish-dialog-title-${story.id}`}
            >
              <div className="dialog-title" id={`unpublish-dialog-title-${story.id}`}>
                Unpublish &ldquo;{storyLabel}&rdquo;?
              </div>
              <div className="dialog-body">
                Are you sure? Unpublishing removes this story from every player&rsquo;s adventure list.
              </div>
              <div className="dialog-actions">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={cancelUnpublish}
                  disabled={status === "working"}
                >
                  Keep it published
                </button>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={confirmUnpublish}
                  disabled={status === "working"}
                >
                  {status === "working" ? "Unpublishing…" : "Unpublish"}
                </button>
              </div>
            </div>
          </div>
        )}
      </td>
    </tr>
  );
}

/**
 * The admin "Stories" destination — a list of the stories that exist, with a
 * per-row publish/unpublish action (FR-010, FR-013, FR-014), so "Stories"
 * and "New story" are distinct places to go (FR-002, SC-007).
 *
 * Editing, the full-configuration view, and deleting stories are
 * deliberately not here; those belong to 012-story-editing-and-review.
 */
export function AdminPage() {
  const { instance, accounts: msalAccounts } = useMsal();
  const account = msalAccounts[0];
  const accountKey = account?.homeAccountId ?? account?.username ?? null;

  const [stories, setStories] = useState([]);
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
    setStories((prev) => prev.map((s) => (s.id === updatedStory.id ? updatedStory : s)));
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
              <th scope="col">Actions</th>
            </tr>
          </thead>
          <tbody>
            {stories.map((story) => (
              <StoryRow key={story.id} story={story} getToken={getToken} onStoryChange={handleStoryChange} />
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default AdminPage;
