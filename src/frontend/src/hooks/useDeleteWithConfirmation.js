import { useState } from "react";

/**
 * Shared delete-call + confirmation state machine behind both `useDeleteStory.js`
 * (025-story-delete-done) and `useDeleteSession.js` (028-home-page-redesign) — factored
 * out after `/code-review high` flagged the two as byte-for-byte duplicates of the same
 * idle/working/error + confirm/cancel lifecycle.
 *
 * `token` may be a plain access-token string or an async function returning one.
 * `deleteFn(resolvedToken, id)` performs the actual delete call.
 * `onDeleted(id)` fires once the delete succeeds (or, with `treatNotFoundAsSuccess`, once
 * a 404 confirms it was already gone).
 */
export function useDeleteWithConfirmation(token, id, deleteFn, onDeleted, { treatNotFoundAsSuccess = false } = {}) {
  const [status, setStatus] = useState("idle"); // idle | working | error
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  const resolveToken = async () => (typeof token === "function" ? token() : token);

  const requestDelete = () => {
    // Clears a stale error from a previous attempt so reopening the dialog doesn't
    // show both the old error alert and the fresh confirmation at once.
    setStatus("idle");
    setConfirmingDelete(true);
  };
  const cancelDelete = () => setConfirmingDelete(false);

  const confirmDelete = async () => {
    setStatus("working");
    try {
      const resolvedToken = await resolveToken();
      await deleteFn(resolvedToken, id);
      setStatus("idle");
      setConfirmingDelete(false);
      onDeleted?.(id);
    } catch (err) {
      if (treatNotFoundAsSuccess && err?.response?.status === 404) {
        setStatus("idle");
        setConfirmingDelete(false);
        onDeleted?.(id);
        return;
      }
      setStatus("error");
      setConfirmingDelete(false);
    }
  };

  return {
    status,
    confirmingDelete,
    requestDelete,
    confirmDelete,
    cancelDelete,
  };
}

export default useDeleteWithConfirmation;
