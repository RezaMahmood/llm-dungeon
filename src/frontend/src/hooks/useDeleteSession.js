import { deleteSession } from "../services/gameService.js";
import { useDeleteWithConfirmation } from "./useDeleteWithConfirmation.js";

/**
 * Delete call + confirmation state for one saved session (028-home-page-redesign
 * FR-008/FR-009), sharing `useDeleteStory.js`'s state machine via
 * `useDeleteWithConfirmation` so both destructive confirmations in the product behave
 * identically.
 *
 * `token` may be a plain access-token string or an async function returning one, matching
 * `useDeleteStory`'s own `token` contract.
 *
 * A 404 (the session is already gone — e.g. a double-click) is treated the same as
 * success (contracts/api.md): the caller's `onDeleted` still fires.
 */
export function useDeleteSession(token, session, onDeleted) {
  // A wrapper, not the bare import, so the module binding is only dereferenced when a
  // delete is actually confirmed — not on every render (mattered for test mocks that
  // don't stub this call because nothing in that test ever clicks Delete).
  return useDeleteWithConfirmation(token, session.sessionId, (t, id) => deleteSession(t, id), onDeleted, {
    treatNotFoundAsSuccess: true,
  });
}

export default useDeleteSession;
