import { useMsal } from "@azure/msal-react";
import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import StepNameCover from "../components/Admin/StoryWizard/StepNameCover.jsx";
import StepSessionLength from "../components/Admin/StoryWizard/StepSessionLength.jsx";
import StepToneReadingLevel from "../components/Admin/StoryWizard/StepToneReadingLevel.jsx";
import StepWorldSetting from "../components/Admin/StoryWizard/StepWorldSetting.jsx";
import { loginRequest } from "../services/msalConfig.js";
import { createStory, deleteStory, suggestOutline, updateStory, uploadCoverImage } from "../services/storyService.js";

// Holds this session's in-progress, unsaved field values in browser local storage (FR-010,
// User Story 2) so tab switching before Save never loses data. Unlike the earlier
// server-side StoryDraft/Cosmos-TTL design, this is purely a frontend concern — nothing
// about it is ever sent to the backend until an explicit Save.
const DRAFT_STORAGE_KEY = "llmdungeon.storyWizard.draft";

function emptyFields() {
  return {
    name: "",
    coverImageUrl: null,
    tone: "",
    readingLevel: "",
    sessionLengthMinutes: "",
    chapters: "",
    outline: "",
    rules: "",
    characterTypes: [],
    completionCriteria: null,
  };
}

function loadStoredDraft() {
  try {
    const raw = localStorage.getItem(DRAFT_STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function writeStoredDraft(draft) {
  try {
    localStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(draft));
  } catch {
    // Local storage unavailable (e.g. private browsing) — only unsaved, in-progress
    // input is at risk (Edge Cases); anything already persisted via a prior Save is
    // unaffected.
  }
}

function clearStoredDraft() {
  try {
    localStorage.removeItem(DRAFT_STORAGE_KEY);
  } catch {
    // no-op
  }
}

/** Strips still-being-typed, not-yet-valid rows (an added character type with no name
 * yet, an added condition with no text yet) before a Save reaches the backend — the
 * dedicated-field components intentionally hold those locally without calling `onChange`
 * until they're valid, but a still-empty row can survive a page reload via localStorage,
 * so this is enforced again here, at the Save boundary. */
function toApiPayload(fields) {
  const characterTypes = (fields.characterTypes || []).filter((ct) => ct.name && ct.name.trim());

  let completionCriteria = fields.completionCriteria;
  if (completionCriteria) {
    const successConditions = (completionCriteria.successConditions || []).filter((c) => c && c.trim());
    const failureConditions = (completionCriteria.failureConditions || []).filter((c) => c && c.trim());
    if (successConditions.length === 0) {
      completionCriteria = null;
    } else {
      const totalConditions = successConditions.length + failureConditions.length;
      completionCriteria = {
        maxDurationMinutes: completionCriteria.maxDurationMinutes ?? null,
        successConditions,
        failureConditions,
        rule: totalConditions > 1 ? completionCriteria.rule || "any" : null,
      };
    }
  }

  return {
    name: fields.name || "",
    tone: fields.tone || null,
    readingLevel: fields.readingLevel || null,
    sessionLengthMinutes: fields.sessionLengthMinutes ? Number(fields.sessionLengthMinutes) : null,
    chapters: fields.chapters ? Number(fields.chapters) : null,
    outline: fields.outline || null,
    rules: fields.rules || null,
    characterTypes,
    completionCriteria,
  };
}

function storyToFields(story) {
  return {
    name: story.name || "",
    coverImageUrl: story.coverImageUrl || null,
    tone: story.tone || "",
    readingLevel: story.readingLevel || "",
    sessionLengthMinutes: story.sessionLengthMinutes ?? "",
    chapters: story.chapters ?? "",
    outline: story.outline || "",
    rules: story.rules || "",
    characterTypes: story.characterTypes || [],
    completionCriteria: story.completionCriteria || null,
  };
}

const STEPS = [
  {
    key: "name-cover",
    number: "01",
    label: "Name & cover",
    description: "What players see in their list.",
    Component: StepNameCover,
  },
  {
    key: "world-setting",
    number: "02",
    label: "World & setting",
    description: "The engine improvises everything from this. Write it like you are telling a colleague about the place.",
    Component: StepWorldSetting,
  },
  {
    key: "tone-reading-level",
    number: "03",
    label: "Tone & reading level",
    description: "Sets the voice and vocabulary the narrator keeps to.",
    Component: StepToneReadingLevel,
  },
  {
    key: "session-length",
    number: "04",
    label: "Session length",
    description: "How long a sitting runs before a natural place to stop.",
    Component: StepSessionLength,
  },
];

export function AdminStoryWizardPage() {
  const { instance, accounts: msalAccounts } = useMsal();
  const account = msalAccounts[0];
  const accountKey = account?.homeAccountId ?? account?.username ?? null;
  const navigate = useNavigate();

  const [token, setToken] = useState(null);
  const [storyId, setStoryId] = useState(() => loadStoredDraft()?.storyId ?? null);
  const [fields, setFields] = useState(() => loadStoredDraft()?.fields ?? emptyFields());
  const [pendingCoverImageFile, setPendingCoverImageFile] = useState(null);
  const [activeStep, setActiveStep] = useState(STEPS[0].key);
  const [saveStatus, setSaveStatus] = useState("idle"); // idle | saving | saved | error | name-required
  const [confirmAction, setConfirmAction] = useState(null); // null | "abandon" | "finished"
  const [actionStatus, setActionStatus] = useState("idle"); // idle | working | error

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const tokenResponse = await instance.acquireTokenSilent({ ...loginRequest, account });
      if (!cancelled) setToken(tokenResponse.accessToken);
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- accountKey is the stable dependency
  }, [instance, accountKey]);

  // Every field change (any tab) is written straight to local storage (FR-010) — nothing
  // reaches the backend until Save.
  useEffect(() => {
    writeStoredDraft({ storyId, fields });
  }, [storyId, fields]);

  const updateFields = useCallback((patch) => {
    setFields((current) => ({ ...current, ...patch }));
    setSaveStatus("idle");
  }, []);

  const handleSuggestOutline = useCallback(
    async (idea) => {
      const data = await suggestOutline(token, idea);
      return data.outline;
    },
    [token],
  );

  const handleSave = useCallback(async () => {
    if (!storyId && !fields.name.trim()) {
      setSaveStatus("name-required");
      return;
    }

    setSaveStatus("saving");
    try {
      const payload = toApiPayload(fields);
      const data = storyId ? await updateStory(token, storyId, payload) : await createStory(token, payload);
      let story = data.story;

      if (pendingCoverImageFile) {
        const uploaded = await uploadCoverImage(token, story.id, pendingCoverImageFile);
        story = uploaded.story;
        setPendingCoverImageFile(null);
      }

      setStoryId(story.id);
      setFields(storyToFields(story));
      setSaveStatus("saved");
    } catch {
      setSaveStatus("error");
    }
  }, [token, storyId, fields, pendingCoverImageFile]);

  const handleConfirmAbandon = useCallback(async () => {
    setActionStatus("working");
    try {
      if (storyId) {
        await deleteStory(token, storyId);
      }
      clearStoredDraft();
      navigate("/admin");
    } catch {
      setActionStatus("error");
    }
  }, [token, storyId, navigate]);

  const handleConfirmFinished = useCallback(() => {
    clearStoredDraft();
    navigate("/admin");
  }, [navigate]);

  if (!token) {
    return (
      <div style={{ padding: "var(--space-6)" }}>
        <p className="text-muted">Starting a new story…</p>
      </div>
    );
  }

  const activeStepConfig = STEPS.find((step) => step.key === activeStep);
  const ActiveStep = activeStepConfig.Component;

  return (
    <div style={{ maxWidth: "1080px", padding: "var(--space-6) var(--space-4) 64px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", gap: "var(--space-4)", flexWrap: "wrap" }}>
        <h1 style={{ margin: 0 }}>New story</h1>
        <div style={{ display: "flex", gap: "10px", alignItems: "center", flexWrap: "wrap" }}>
          {saveStatus === "saved" && (
            <span className="text-muted" style={{ fontSize: "13px" }}>
              Saved
            </span>
          )}
          {saveStatus === "name-required" && (
            <span role="alert" className="text-muted" style={{ fontSize: "13px" }}>
              A story name is required to save.
            </span>
          )}
          {saveStatus === "error" && (
            <span role="alert" className="text-muted" style={{ fontSize: "13px" }}>
              Could not save. Please try again.
            </span>
          )}
          <button type="button" className="btn btn-secondary" onClick={() => setConfirmAction("abandon")}>
            Abandon
          </button>
          <button type="button" className="btn btn-secondary" onClick={() => setConfirmAction("finished")}>
            Finished
          </button>
          <button type="button" className="btn btn-primary" onClick={handleSave} disabled={saveStatus === "saving"}>
            {saveStatus === "saving" ? "Saving…" : "Save"}
          </button>
        </div>
      </div>
      <hr className="hr" />

      <div
        role="tablist"
        style={{
          display: "flex",
          gap: "2px",
          background: "var(--color-divider)",
          border: "1px solid var(--color-divider)",
          marginBottom: "var(--space-6)",
          overflow: "hidden",
        }}
      >
        {STEPS.map((step) => {
          const isActive = step.key === activeStep;
          return (
            <button
              key={step.key}
              type="button"
              role="tab"
              aria-selected={isActive}
              onClick={() => setActiveStep(step.key)}
              style={{
                flex: 1,
                background: "var(--color-bg)",
                border: 0,
                cursor: "pointer",
                textAlign: "left",
                padding: "12px 14px",
                fontFamily: "var(--font-body)",
                color: "inherit",
                display: "flex",
                flexDirection: "column",
                gap: "4px",
              }}
            >
              <span className="ovnum" style={{ fontSize: "26px" }}>
                {step.number}
              </span>
              <span style={{ fontSize: "12px", letterSpacing: "0.06em", textTransform: "uppercase" }}>{step.label}</span>
            </button>
          );
        })}
      </div>

      <div style={{ display: "flex", alignItems: "flex-end", gap: "14px" }}>
        <span className="ovnum" style={{ fontSize: "64px", color: "var(--color-accent)" }}>
          {activeStepConfig.number}
        </span>
        <h3 style={{ margin: "0 0 6px" }}>{activeStepConfig.label}</h3>
      </div>
      <p className="text-muted" style={{ margin: "14px 0 24px", fontSize: "14px", maxWidth: "56ch" }}>
        {activeStepConfig.description}
      </p>

      <ActiveStep
        fields={fields}
        onChange={updateFields}
        onSuggestOutline={handleSuggestOutline}
        pendingCoverImageFile={pendingCoverImageFile}
        onCoverImageFileSelected={setPendingCoverImageFile}
      />

      {confirmAction && (
        <div className="dialog-backdrop">
          <div className="dialog" role="dialog" aria-modal="true">
            <div className="dialog-title">{confirmAction === "abandon" ? "Abandon this story?" : "Finish this creation session?"}</div>
            <div className="dialog-body">
              {confirmAction === "abandon"
                ? "Unsaved changes are discarded, and if this story was ever saved, that record is deleted. This cannot be undone."
                : "Whatever has already been saved — complete or partial — stays saved. You can come back and edit it later."}
            </div>
            {actionStatus === "error" && (
              <div role="alert" className="text-muted">
                Something went wrong. Please try again.
              </div>
            )}
            <div className="dialog-actions">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => {
                  setConfirmAction(null);
                  setActionStatus("idle");
                }}
                disabled={actionStatus === "working"}
              >
                Keep working
              </button>
              <button
                type="button"
                className="btn btn-primary"
                onClick={confirmAction === "abandon" ? handleConfirmAbandon : handleConfirmFinished}
                disabled={actionStatus === "working"}
              >
                {confirmAction === "abandon" ? (actionStatus === "working" ? "Abandoning…" : "Abandon") : "Finished"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default AdminStoryWizardPage;
