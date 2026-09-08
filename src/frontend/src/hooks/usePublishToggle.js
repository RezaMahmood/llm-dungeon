import { useState } from "react";

import { publishStory, unpublishStory } from "../services/storyDraftService.js";

/**
 * Shared publish/unpublish call + FR-011 gate-message + FR-013 confirmation
 * state, used by both the wizard's `StepPublish` step and the administrator
 * story list's per-row action (005-story-publishing-done Phase 5) so there is
 * exactly one implementation of this flow.
 *
 * `token` may be a plain access-token string (the wizard already has one) or
 * an async function returning one (the story list acquires it lazily per
 * click via `acquireTokenSilent`).
 *
 * `onPublished` (010-story-test-play, optional): called with the updated story after a
 * confirmed publish succeeds, in addition to `onStoryChange`. Lets the test-play
 * conclusion screen navigate away on success without a separate publish path.
 */
export function usePublishToggle(token, story, onStoryChange, onPublished) {
  const [status, setStatus] = useState("idle"); // idle | working | error
  const [gateMessage, setGateMessage] = useState(null);
  const [confirmingUnpublish, setConfirmingUnpublish] = useState(false);
  const [confirmingPublish, setConfirmingPublish] = useState(false);

  const resolveToken = async () => (typeof token === "function" ? token() : token);

  const requestPublish = () => {
    setGateMessage(null);
    setConfirmingPublish(true);
  };
  const cancelPublish = () => setConfirmingPublish(false);

  const confirmPublish = async () => {
    setStatus("working");
    setGateMessage(null);
    try {
      const resolvedToken = await resolveToken();
      const data = await publishStory(resolvedToken, story.id);
      onStoryChange?.(data.story);
      onPublished?.(data.story);
      setStatus("idle");
      setConfirmingPublish(false);
    } catch (err) {
      setConfirmingPublish(false);
      if (err?.response?.status === 409) {
        setGateMessage(err.response.data?.message || "This story cannot be published yet.");
        setStatus("idle");
      } else {
        setStatus("error");
      }
    }
  };

  const requestUnpublish = () => setConfirmingUnpublish(true);
  const cancelUnpublish = () => setConfirmingUnpublish(false);

  const confirmUnpublish = async () => {
    setStatus("working");
    try {
      const resolvedToken = await resolveToken();
      const data = await unpublishStory(resolvedToken, story.id);
      onStoryChange?.(data.story);
      setStatus("idle");
      setConfirmingUnpublish(false);
    } catch {
      setStatus("error");
      setConfirmingUnpublish(false);
    }
  };

  return {
    status,
    gateMessage,
    confirmingUnpublish,
    confirmingPublish,
    requestPublish,
    confirmPublish,
    cancelPublish,
    requestUnpublish,
    confirmUnpublish,
    cancelUnpublish,
  };
}

export default usePublishToggle;
