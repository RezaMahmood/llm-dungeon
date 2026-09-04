import { useState } from "react";

import { publishStory, unpublishStory } from "../../../services/storyDraftService.js";

export function StepPublish({ story, token, onStoryChange }) {
  const [status, setStatus] = useState("idle"); // idle | working | error
  const [gateMessage, setGateMessage] = useState(null);
  const [confirmingUnpublish, setConfirmingUnpublish] = useState(false);

  const handlePublish = async () => {
    setStatus("working");
    setGateMessage(null);
    try {
      const data = await publishStory(token, story.id);
      onStoryChange?.(data.story);
      setStatus("idle");
    } catch (err) {
      if (err?.response?.status === 409) {
        setGateMessage(err.response.data?.message || "This story cannot be published yet.");
        setStatus("idle");
      } else {
        setStatus("error");
      }
    }
  };

  const handleConfirmUnpublish = async () => {
    setStatus("working");
    try {
      const data = await unpublishStory(token, story.id);
      onStoryChange?.(data.story);
      setStatus("idle");
      setConfirmingUnpublish(false);
    } catch {
      setStatus("error");
      setConfirmingUnpublish(false);
    }
  };

  return (
    <div className="field">
      <p>
        Status:{" "}
        <strong>{story.published ? "Published" : "Unpublished"}</strong>
        {story.lastPublishedAt && (
          <span className="text-muted"> — last published {story.lastPublishedAt}</span>
        )}
      </p>

      {!story.published && (
        <button type="button" className="btn btn-primary" disabled={status === "working"} onClick={handlePublish}>
          {status === "working" ? "Publishing…" : "Publish"}
        </button>
      )}

      {story.published && (
        <button
          type="button"
          className="btn btn-secondary"
          disabled={status === "working"}
          onClick={() => setConfirmingUnpublish(true)}
        >
          Unpublish
        </button>
      )}

      {gateMessage && (
        <div role="alert" className="text-muted" style={{ marginTop: "8px" }}>
          {gateMessage}
        </div>
      )}

      {status === "error" && (
        <div role="alert" className="text-muted" style={{ marginTop: "8px" }}>
          Could not update this story's published state. Please try again.
        </div>
      )}

      {confirmingUnpublish && (
        <div className="dialog-backdrop">
          <div className="dialog" role="dialog" aria-modal="true">
            <div className="dialog-title">Unpublish this story?</div>
            <div className="dialog-body">
              Are you sure? Unpublishing removes this story from every player&rsquo;s adventure list.
            </div>
            <div className="dialog-actions">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setConfirmingUnpublish(false)}
                disabled={status === "working"}
              >
                Keep it published
              </button>
              <button
                type="button"
                className="btn btn-primary"
                onClick={handleConfirmUnpublish}
                disabled={status === "working"}
              >
                {status === "working" ? "Unpublishing…" : "Unpublish"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default StepPublish;
