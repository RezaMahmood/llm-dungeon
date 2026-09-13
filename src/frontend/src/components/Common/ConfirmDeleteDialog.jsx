/**
 * Shared confirmation dialog behind every destructive-delete action in the product
 * (`Admin/StoryDeleteAction.jsx`, `Home/SessionDeleteAction.jsx`) — factored out after
 * `/code-review high` flagged the two as near-identical copies of the same dialog markup.
 * Built from the design system's `.dialog`/`.dialog-backdrop` primitives (Principle VIII);
 * never a browser-native `confirm()`.
 *
 * Both buttons go inert while the delete is in flight and the confirm button spins
 * (issue #347) — the delete itself is the slow, material call, so this dialog is where
 * the pending state matters most.
 */
import PendingButton from "./PendingButton.jsx";

export function ConfirmDeleteDialog({
  titleId,
  title,
  body,
  cancelLabel = "Cancel",
  confirmLabel = "Delete",
  workingLabel = "Deleting…",
  working = false,
  onCancel,
  onConfirm,
}) {
  return (
    <div className="dialog-backdrop" onClick={onCancel}>
      <div
        className="dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="dialog-title" id={titleId}>
          {title}
        </div>
        <div className="dialog-body">{body}</div>
        <div className="dialog-actions">
          {/* Cancel is greyed out too, but never spins: only one thing is in flight, and
              it isn't this one. */}
          <PendingButton className="btn btn-secondary" onClick={onCancel} disabled={working}>
            {cancelLabel}
          </PendingButton>
          <PendingButton className="btn btn-primary" onClick={onConfirm} pending={working} pendingLabel={workingLabel}>
            {confirmLabel}
          </PendingButton>
        </div>
      </div>
    </div>
  );
}

export default ConfirmDeleteDialog;
