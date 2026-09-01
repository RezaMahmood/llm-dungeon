import { useState } from "react";

import { publishStory, unpublishStory } from "../../../services/storyDraftService.js";

// Publish/unpublish for a persisted Story (005-story-publishing). Unlike the other wizard
// steps this does not act on a StoryDraft — it runs after generation, against the story's
// own id. FR-011: a blocked publish attempt shows the server's explanatory text rather than
// a silent/unexplained disabled control. FR-013: unpublish requires a client-only "are you
// sure?" confirmation before the request is sent — publishing itself needs no confirmation.
export function StepPublish({ token, story, onStoryChange }) {
  const [status, setStatus] = useState("idle"); // idle | working | error
  const [blockedMessage, setBlockedMessage] = useState(null);
  const [confirmingUnpublish, setConfirmingUnpublish] = useState(false);

  const handlePublish = async () => {
    setStatus("working");
    setBlockedMessage(null);
    try {
      const data = await publishStory(token, story.id);
      onStoryChange(data.story);
      setStatus("idle");
    } catch (err) {
      const body = err?.response?.data;
      if (err?.response?.status === 409 && body?.message) {
        setBlockedMessage(body.message);
        setStatus("idle");
      } else {
        setStatus("error");
      }
    }
  };

  const handleUnpublish = async () => {
    setConfirmingUnpublish(false);
    setStatus("working");
    try {
      const data = await unpublishStory(token, story.id);
      onStoryChange(data.story);
      setStatus("idle");
    } catch {
      setStatus("error");
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
      <p className="text-muted" style={{ margin: 0 }}>
        {story.published
          ? "This story is published — it is visible to every player in their adventure list."
          : "This story is unpublished — players cannot see or start it yet."}
      </p>
      {story.lastPublishedAt && (
        <p className="text-muted" style={{ margin: 0, fontSize: "13px" }}>
          Last published {new Date(story.lastPublishedAt).toLocaleString()}.
        </p>
      )}

      {!story.published && (
        <div style={{ display: "flex", flexDirection: "column", gap: "8px", alignItems: "flex-start" }}>
          <button type="button" className="btn btn-primary" onClick={handlePublish} disabled={status === "working"}>
            {status === "working" ? "Publishing…" : "Publish"}
          </button>
          {blockedMessage && (
            <p role="alert" className="text-muted" style={{ margin: 0 }}>
              {blockedMessage}
            </p>
          )}
        </div>
      )}

      {story.published && !confirmingUnpublish && (
        <button
          type="button"
          className="btn"
          onClick={() => setConfirmingUnpublish(true)}
          disabled={status === "working"}
        >
          Unpublish
        </button>
      )}

      {story.published && confirmingUnpublish && (
        <div style={{ display: "flex", flexDirection: "column", gap: "8px", alignItems: "flex-start" }}>
          <p role="alert" style={{ margin: 0 }}>
            Are you sure? Unpublishing removes this story from every player&rsquo;s adventure list. Play sessions
            already in progress are not affected.
          </p>
          <div style={{ display: "flex", gap: "12px" }}>
            <button type="button" className="btn btn-primary" onClick={handleUnpublish} disabled={status === "working"}>
              {status === "working" ? "Unpublishing…" : "Yes, unpublish"}
            </button>
            <button type="button" className="btn" onClick={() => setConfirmingUnpublish(false)}>
              Cancel
            </button>
          </div>
        </div>
      )}

      {status === "error" && (
        <p role="alert" className="text-muted" style={{ margin: 0 }}>
          Could not update the publish status. Please try again.
        </p>
      )}
    </div>
  );
}

export default StepPublish;
