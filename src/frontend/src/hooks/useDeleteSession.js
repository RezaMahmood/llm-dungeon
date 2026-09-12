import { useState } from "react";

import { deleteSession } from "../services/gameService.js";

/**
 * Delete call + confirmation state for one saved session (028-home-page-redesign
 * FR-008/FR-009), mirroring `useDeleteStory.js`'s shape so both destructive
 * confirmations in the product behave identically.
 *
 * `token` may be a plain access-token string or an async function returning one, matching
 * `useDeleteStory`'s own `token` contract.
 *
 * A 404 (the session is already gone — e.g. a double-click) is treated the same as
 * success (contracts/api.md): the caller's `onDeleted` still fires.
 */
export function useDeleteSession(token, session, onDeleted) {
  const [status, setStatus] = useState("idle"); // idle | working | error
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  const resolveToken = async () => (typeof token === "function" ? token() : token);

  const requestDelete = () => setConfirmingDelete(true);
  const cancelDelete = () => setConfirmingDelete(false);

  const confirmDelete = async () => {
    setStatus("working");
    try {
      const resolvedToken = await resolveToken();
      await deleteSession(resolvedToken, session.sessionId);
      setStatus("idle");
      setConfirmingDelete(false);
      onDeleted?.(session.sessionId);
    } catch (err) {
      if (err.response?.status === 404) {
        setStatus("idle");
        setConfirmingDelete(false);
        onDeleted?.(session.sessionId);
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

export default useDeleteSession;
