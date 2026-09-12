import ConfirmDeleteDialog from "../Common/ConfirmDeleteDialog.jsx";
import { useDeleteStory } from "../../hooks/useDeleteStory.js";

/**
 * Permanent delete for one story plus its confirmation dialog (025-story-delete-done FR-001,
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
        <ConfirmDeleteDialog
          titleId={dialogTitleId}
          title={<>Delete &ldquo;{storyLabel}&rdquo;?</>}
          body={
            <>
              This is permanent and cannot be undone. Deleting this story will also remove any
              players&rsquo; in-progress games for it. If you might want this story back later, unpublish it
              instead.
            </>
          }
          cancelLabel="Keep it"
          working={status === "working"}
          onCancel={cancelDelete}
          onConfirm={confirmDelete}
        />
      )}
    </div>
  );
}

export default StoryDeleteAction;
