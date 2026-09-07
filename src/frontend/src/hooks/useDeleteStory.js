import { useState } from "react";

import { deleteStory } from "../services/storyDraftService.js";

/**
 * Delete call + confirmation state for one story (025-story-delete FR-002), mirroring
 * `usePublishToggle`'s shape so the admin story list's delete action follows the same
 * pattern as its publish/unpublish action.
 *
 * `token` may be a plain access-token string or an async function returning one (the
 * story list resolves it lazily per click).
 *
 * Unlike `usePublishToggle`'s `onStoryChange`, there is nothing left to describe once a
 * story is deleted — `onDeleted` is called with just the story's id so the caller can
 * remove it from its own list state.
 */
export function useDeleteStory(token, story, onDeleted) {
  const [status, setStatus] = useState("idle"); // idle | working | error
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  const resolveToken = async () => (typeof token === "function" ? token() : token);

  const requestDelete = () => setConfirmingDelete(true);
  const cancelDelete = () => setConfirmingDelete(false);

  const confirmDelete = async () => {
    setStatus("working");
    try {
      const resolvedToken = await resolveToken();
      await deleteStory(resolvedToken, story.id);
      setStatus("idle");
      setConfirmingDelete(false);
      onDeleted?.(story.id);
    } catch {
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

export default useDeleteStory;
