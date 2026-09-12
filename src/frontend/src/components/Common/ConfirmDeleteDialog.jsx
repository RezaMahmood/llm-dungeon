/**
 * Shared confirmation dialog behind every destructive-delete action in the product
 * (`Admin/StoryDeleteAction.jsx`, `Home/SessionDeleteAction.jsx`) — factored out after
 * `/code-review high` flagged the two as near-identical copies of the same dialog markup.
 * Built from the design system's `.dialog`/`.dialog-backdrop` primitives (Principle VIII);
 * never a browser-native `confirm()`.
 */
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
          <button type="button" className="btn btn-secondary" onClick={onCancel} disabled={working}>
            {cancelLabel}
          </button>
          <button type="button" className="btn btn-primary" onClick={onConfirm} disabled={working}>
            {working ? workingLabel : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

export default ConfirmDeleteDialog;
