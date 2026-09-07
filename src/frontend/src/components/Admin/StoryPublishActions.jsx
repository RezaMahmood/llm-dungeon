import { usePublishToggle } from "../../hooks/usePublishToggle.js";

/**
 * Publish/unpublish for one story plus its confirmation dialog — shared by the story
 * wizard's terminal step and each row of the admin story list (FR-011,
 * research.md §11), so both entry points enforce the identical `005` FR-010 precondition
 * and gate explanation rather than a parallel reimplementation (Principle VIII).
 *
 * `token` may be a plain access-token string (the wizard already has one by the time this
 * renders) or an async function returning one (the story list resolves it lazily per click
 * via `usePublishToggle`, so a click is never sent with a stale or missing token).
 */
export function StoryPublishActions({ story, token, onStoryChange }) {
  const {
    status,
    gateMessage,
    confirmingUnpublish,
    handlePublish,
    requestUnpublish,
    confirmUnpublish,
    cancelUnpublish,
  } = usePublishToggle(token, story, onStoryChange);

  const storyLabel = story.name || "this story";
  const dialogTitleId = `unpublish-dialog-title-${story.id}`;

  return (
    <div className="field">
      <p>
        Status:{" "}
        <strong>{story.published ? "Published" : "Unpublished"}</strong>
        {story.lastPublishedAt && (
          <span className="text-muted"> — last published {story.lastPublishedAt}</span>
        )}
      </p>

      {!story.published && (
        <button type="button" className="btn btn-primary" disabled={status === "working"} onClick={handlePublish}>
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
        <div role="alert" className="text-muted" style={{ marginTop: "8px" }}>
          {gateMessage}
        </div>
      )}

      {status === "error" && (
        <div role="alert" className="text-muted" style={{ marginTop: "8px" }}>
          Could not update this story's published state. Please try again.
        </div>
      )}

      {confirmingUnpublish && (
        <div className="dialog-backdrop">
          <div className="dialog" role="dialog" aria-modal="true" aria-labelledby={dialogTitleId}>
            <div className="dialog-title" id={dialogTitleId}>
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
    </div>
  );
}

export default StoryPublishActions;
