import { useDeleteStory } from "../../hooks/useDeleteStory.js";

/**
 * Permanent delete for one story plus its confirmation dialog (025-story-delete FR-001,
 * FR-002), mirroring `StoryPublishActions.jsx`'s dialog pattern (Principle VIII) but with
 * copy distinct from unpublish's — this action is permanent, cannot be undone, and also
 * removes any players' in-progress games for this story (FR-004).
 *
 * `token` may be a plain access-token string or an async function returning one, matching
 * `StoryPublishActions`'s own `token` contract.
 */
export function StoryDeleteAction({ story, token, onDeleted }) {
  const { status, confirmingDelete, requestDelete, confirmDelete, cancelDelete } = useDeleteStory(
    token,
    story,
    onDeleted,
  );

  const storyLabel = story.name || "this story";
  const dialogTitleId = `delete-dialog-title-${story.id}`;

  return (
    <div className="field">
      <button type="button" className="btn btn-secondary" disabled={status === "working"} onClick={requestDelete}>
        Delete
      </button>

      {status === "error" && (
        <div role="alert" className="text-muted" style={{ marginTop: "8px" }}>
          Could not delete this story. Please try again.
        </div>
      )}

      {confirmingDelete && (
        <div className="dialog-backdrop">
          <div className="dialog" role="dialog" aria-modal="true" aria-labelledby={dialogTitleId}>
            <div className="dialog-title" id={dialogTitleId}>
              Delete &ldquo;{storyLabel}&rdquo;?
            </div>
            <div className="dialog-body">
              This is permanent and cannot be undone. Deleting this story will also remove any
              players&rsquo; in-progress games for it. If you might want this story back later, unpublish it
              instead.
            </div>
            <div className="dialog-actions">
              <button type="button" className="btn btn-secondary" onClick={cancelDelete} disabled={status === "working"}>
                Keep it
              </button>
              <button type="button" className="btn btn-primary" onClick={confirmDelete} disabled={status === "working"}>
                {status === "working" ? "Deleting…" : "Delete"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default StoryDeleteAction;
