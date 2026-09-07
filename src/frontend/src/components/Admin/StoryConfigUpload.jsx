import { useState } from "react";

import { importStoryConfiguration } from "../../services/storyDraftService.js";

/**
 * The story list's upload entry point (FR-005): pick a configuration file, confirm the
 * named overwrite target for an id-carrying file or prompt for a title on an id-less one,
 * and surface every server rejection verbatim. The pre-flight checks here are a strict
 * subset of the server's rules — parseable, an object, required keys present — so this
 * component never rejects a file the server would accept, and never invents a rejection
 * reason the server would not also give (contracts/api.md → Validation runs on both
 * sides; research.md §7).
 *
 * `token` may be a plain access-token string or an async function returning one, resolved
 * lazily at submit time — matching `usePublishToggle`'s pattern — so a click is never sent
 * with a stale or missing token.
 */
function preflightValidate(parsed) {
  if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
    return "The file must contain a JSON object.";
  }
  if (parsed.id && !parsed.name) {
    return "name: a name is required when overwriting an existing story";
  }
  if (!parsed.worldPrompt) {
    return "worldPrompt: a world prompt is required";
  }
  if (!Array.isArray(parsed.characterTypes) || parsed.characterTypes.length === 0) {
    return "characterTypes: at least one character type is required";
  }
  if (!parsed.completionCriteria?.successConditions?.length) {
    return "completionCriteria.successConditions: at least one success condition is required";
  }
  return null;
}

export function StoryConfigUpload({ token, onImported }) {
  const [status, setStatus] = useState("idle"); // idle | working
  const [errorMessage, setErrorMessage] = useState(null);
  const [pendingFile, setPendingFile] = useState(null); // { text }
  const [confirmOverwriteStoryId, setConfirmOverwriteStoryId] = useState(null);
  const [titlePromptNeeded, setTitlePromptNeeded] = useState(false);
  const [title, setTitle] = useState("");

  const reset = () => {
    setPendingFile(null);
    setConfirmOverwriteStoryId(null);
    setTitlePromptNeeded(false);
    setTitle("");
  };

  const handleFileChange = async (event) => {
    const file = event.target.files?.[0];
    event.target.value = ""; // allow re-selecting the same file after a rejection
    if (!file) return;
    reset();
    setErrorMessage(null);

    const text = await file.text();
    let parsed;
    try {
      parsed = JSON.parse(text);
    } catch (err) {
      setErrorMessage(`The file is not valid JSON (${err.message})`);
      return;
    }

    const preflightError = preflightValidate(parsed);
    if (preflightError) {
      setErrorMessage(preflightError);
      return;
    }

    setPendingFile({ text });
    if (parsed.id) {
      setConfirmOverwriteStoryId(parsed.id);
    } else {
      setTitlePromptNeeded(true);
    }
  };

  const submit = async (body) => {
    setStatus("working");
    setErrorMessage(null);
    try {
      const resolvedToken = typeof token === "function" ? await token() : token;
      const data = await importStoryConfiguration(resolvedToken, body);
      setStatus("idle");
      reset();
      onImported?.(data);
    } catch (err) {
      setStatus("idle");
      setErrorMessage(err?.response?.data?.message || "Could not import this file. Please try again.");
    }
  };

  const handleConfirmOverwrite = () => {
    submit({ configurationText: pendingFile.text, confirmOverwriteStoryId });
  };

  const handleSubmitTitle = (event) => {
    event.preventDefault();
    submit({ configurationText: pendingFile.text, title });
  };

  return (
    <div className="field">
      <label htmlFor="story-config-upload">Upload configuration file</label>
      <input
        id="story-config-upload"
        type="file"
        accept="application/json"
        onChange={handleFileChange}
        disabled={status === "working"}
      />

      {errorMessage && (
        <div role="alert" className="text-muted" style={{ marginTop: "8px" }}>
          {errorMessage}
        </div>
      )}

      {confirmOverwriteStoryId && (
        <div className="dialog-backdrop">
          <div className="dialog" role="dialog" aria-modal="true" aria-labelledby="overwrite-dialog-title">
            <div className="dialog-title" id="overwrite-dialog-title">
              Overwrite this story?
            </div>
            <div className="dialog-body">
              This uploads a new configuration for story {confirmOverwriteStoryId}, replacing its current content.
            </div>
            <div className="dialog-actions">
              <button type="button" className="btn btn-secondary" onClick={reset} disabled={status === "working"}>
                Cancel
              </button>
              <button
                type="button"
                className="btn btn-primary"
                onClick={handleConfirmOverwrite}
                disabled={status === "working"}
              >
                {status === "working" ? "Uploading…" : "Overwrite"}
              </button>
            </div>
          </div>
        </div>
      )}

      {titlePromptNeeded && (
        <div className="dialog-backdrop">
          <form onSubmit={handleSubmitTitle} className="dialog" role="dialog" aria-modal="true" aria-labelledby="title-dialog-title">
            <div className="dialog-title" id="title-dialog-title">
              Name this new story
            </div>
            <div className="field">
              <label htmlFor="new-story-title">Title</label>
              <input id="new-story-title" value={title} onChange={(event) => setTitle(event.target.value)} required />
            </div>
            <div className="dialog-actions">
              <button type="button" className="btn btn-secondary" onClick={reset} disabled={status === "working"}>
                Cancel
              </button>
              <button type="submit" className="btn btn-primary" disabled={status === "working" || !title}>
                {status === "working" ? "Uploading…" : "Create story"}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}

export default StoryConfigUpload;
