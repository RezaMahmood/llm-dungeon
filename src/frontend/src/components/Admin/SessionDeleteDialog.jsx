import ConfirmDeleteDialog from "../Common/ConfirmDeleteDialog.jsx";

/**
 * The Sessions screen's delete confirmation (08-admin-sessions-spec.md §6, FR-007). Names
 * the session before anything is destroyed, so an administrator can check they are about
 * to delete the row they meant.
 *
 * Wraps the shared `ConfirmDeleteDialog` rather than restating its markup — which is also
 * why the two buttons sit in a row here where the mockup stacks them (research.md
 * Decision 6): every destructive dialog in the product reads the same way.
 *
 * Named `SessionDeleteDialog`, not `SessionDeleteAction`, because
 * `components/Home/SessionDeleteAction.jsx` already exists and is a different thing — the
 * player deleting their own saved game.
 */
export function SessionDeleteDialog({ session, working, onCancel, onConfirm }) {
  return (
    <ConfirmDeleteDialog
      titleId="delete-session-title"
      title="Delete this session?"
      body={`Session ${session.sessionId.slice(0, 8)}… for ${session.email} will be removed, along with its saved progress. This cannot be undone.`}
      cancelLabel="Keep it"
      confirmLabel="Delete session"
      workingLabel="Deleting…"
      working={working}
      onCancel={onCancel}
      onConfirm={onConfirm}
    />
  );
}

export default SessionDeleteDialog;
