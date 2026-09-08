import { usePublishToggle } from "../../hooks/usePublishToggle.js";

/**
 * Publish/unpublish for one story plus its confirmation dialogs — shared by the story
 * wizard's terminal step, each row of the admin story list, and the test-play conclusion
 * screen (FR-011, research.md §11; amended `005` FR-013, 010-story-test-play), so every
 * entry point enforces the identical `005` FR-010 precondition, gate explanation, and
 * publish confirmation rather than a parallel reimplementation (Principle VIII).
 *
 * `token` may be a plain access-token string (the wizard already has one by the time this
 * renders) or an async function returning one (the story list resolves it lazily per click
 * via `usePublishToggle`, so a click is never sent with a stale or missing token).
 *
 * `onPublished` (010-story-test-play, optional): called after a confirmed publish
 * succeeds. Omitted by the story list and `StepPublish`, which keep their in-place
 * behavior; the test-play conclusion screen passes it to navigate to `/admin`.
 */
export function StoryPublishActions({ story, token, onStoryChange, onPublished }) {
  const {
    status,
    gateMessage,
    confirmingUnpublish,
    confirmingPublish,
    requestPublish,
    confirmPublish,
    cancelPublish,
    requestUnpublish,
    confirmUnpublish,
    cancelUnpublish,
  } = usePublishToggle(token, story, onStoryChange, onPublished);

  const storyLabel = story.name || "this story";
  const unpublishDialogTitleId = `unpublish-dialog-title-${story.id}`;
  const publishDialogTitleId = `publish-dialog-title-${story.id}`;

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
        <button type="button" className="btn btn-primary" disabled={status === "working"} onClick={requestPublish}>
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

      {confirmingPublish && (
        <div className="dialog-backdrop">
          <div className="dialog" role="dialog" aria-modal="true" aria-labelledby={publishDialogTitleId}>
            <div className="dialog-title" id={publishDialogTitleId}>
              Publish &ldquo;{storyLabel}&rdquo;?
            </div>
            <div className="dialog-body">
              Are you sure? Publishing makes this story available to every player.
            </div>
            <div className="dialog-actions">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={cancelPublish}
                disabled={status === "working"}
              >
                Not yet
              </button>
              <button
                type="button"
                className="btn btn-primary"
                onClick={confirmPublish}
                disabled={status === "working"}
              >
                {status === "working" ? "Publishing…" : "Publish"}
              </button>
            </div>
          </div>
        </div>
      )}

      {confirmingUnpublish && (
        <div className="dialog-backdrop">
          <div className="dialog" role="dialog" aria-modal="true" aria-labelledby={unpublishDialogTitleId}>
            <div className="dialog-title" id={unpublishDialogTitleId}>
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
