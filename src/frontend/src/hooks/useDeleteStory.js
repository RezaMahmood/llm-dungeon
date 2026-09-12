import { deleteStory } from "../services/storyDraftService.js";
import { useDeleteWithConfirmation } from "./useDeleteWithConfirmation.js";

/**
 * Delete call + confirmation state for one story (025-story-delete-done FR-002), mirroring
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
  // A wrapper, not the bare import — see useDeleteSession.js for why.
  return useDeleteWithConfirmation(token, story.id, (t, id) => deleteStory(t, id), onDeleted);
}

export default useDeleteStory;
