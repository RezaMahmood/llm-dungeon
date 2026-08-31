import { useMsal } from "@azure/msal-react";
import { useCallback, useEffect, useState } from "react";

import StepNameCover from "../components/Admin/StoryWizard/StepNameCover.jsx";
import StepSessionLength from "../components/Admin/StoryWizard/StepSessionLength.jsx";
import StepToneReadingLevel from "../components/Admin/StoryWizard/StepToneReadingLevel.jsx";
import StepWorldSetting from "../components/Admin/StoryWizard/StepWorldSetting.jsx";
import { loginRequest } from "../services/msalConfig.js";
import { createDraft, generateStory, getDraft, patchDraft, postMessage } from "../services/storyDraftService.js";

// Which draft this browser session is currently building. Without this, leaving
// the wizard via the nav bar and coming back would start a brand-new blank
// draft, stranding work the server had already saved (FR-005, SC-003).
const ACTIVE_DRAFT_KEY = "llmdungeon.storyWizard.activeDraftId";

function readActiveDraftId() {
  try {
    return sessionStorage.getItem(ACTIVE_DRAFT_KEY);
  } catch {
    return null;
  }
}

function writeActiveDraftId(draftId) {
  try {
    if (draftId) {
      sessionStorage.setItem(ACTIVE_DRAFT_KEY, draftId);
    } else {
      sessionStorage.removeItem(ACTIVE_DRAFT_KEY);
    }
  } catch {
    // A blocked/full store only costs draft resumption, never the wizard itself.
  }
}

// A failed PATCH is reported next to the field that caused it, in the field's own words —
// not a generic "could not save" banner disconnected from what actually went wrong. Every
// PATCH from a Step component writes exactly one semantic field at a time, so the first key
// in `updates` identifies which field owns the error. `story_draft_service.py`'s
// DraftValidationError messages are "<field>: <reason>" (e.g. "completionCriteria: rule is
// required when more than one condition is defined") — the "<field>: " prefix is stripped
// since the message is already shown right next to that field.
function fieldErrorMessage(err, fieldKey) {
  const backendMessage = err?.response?.data?.message;
  if (!backendMessage) return "Could not save this — please try again.";
  const prefix = `${fieldKey}: `;
  const reason = backendMessage.startsWith(prefix) ? backendMessage.slice(prefix.length) : backendMessage;
  return reason.charAt(0).toUpperCase() + reason.slice(1);
}

// The Completeness Rule (data-model.md) — mirrors StoryDraft.is_complete() on the
// backend, so the wizard can tell the administrator generation is possible without
// waiting on a round trip. Filling this in never generates or navigates by itself
// (#33) — only the explicit "Generate story" action does.
function isReadyToGenerate(draft) {
  return (
    Boolean(draft.worldPrompt) &&
    (draft.characterTypes?.length ?? 0) > 0 &&
    (draft.completionCriteria?.successConditions?.length ?? 0) > 0
  );
}

const STEPS = [
  {
    key: "name-cover",
    number: "01",
    label: "Name & cover",
    description: "What players see in their list.",
    Component: StepNameCover,
    isDone: (draft) => Boolean(draft.name || draft.coverImageUrl),
  },
  {
    key: "world-setting",
    number: "02",
    label: "World & setting",
    description:
      "The engine improvises everything from this. Write it like you are telling a colleague about the place.",
    Component: StepWorldSetting,
    isDone: isReadyToGenerate,
  },
  {
    key: "tone-reading-level",
    number: "03",
    label: "Tone & reading level",
    description: "Sets the voice and vocabulary the narrator keeps to.",
    Component: StepToneReadingLevel,
    isDone: (draft) => Boolean(draft.tone || draft.readingLevel),
  },
  {
    key: "session-length",
    number: "04",
    label: "Session length",
    description: "How long a sitting runs before a natural place to stop.",
    Component: StepSessionLength,
    isDone: (draft) => Boolean(draft.sessionLengthMinutes || draft.chapters),
  },
];

export function AdminStoryWizardPage() {
  const { instance, accounts: msalAccounts } = useMsal();
  const account = msalAccounts[0];
  const accountKey = account?.homeAccountId ?? account?.username ?? null;

  const [token, setToken] = useState(null);
  const [draft, setDraft] = useState(null);
  const [story, setStory] = useState(null);
  const [activeStep, setActiveStep] = useState(STEPS[0].key);
  const [generateStatus, setGenerateStatus] = useState("idle"); // idle | generating | error
  const [fieldErrors, setFieldErrors] = useState({}); // { [fieldKey]: message }

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const tokenResponse = await instance.acquireTokenSilent({ ...loginRequest, account });
      if (cancelled) return;
      setToken(tokenResponse.accessToken);

      // Resume the draft this session was already building, so navigating away
      // via the nav bar and back does not discard saved progress (FR-005).
      const activeDraftId = readActiveDraftId();
      if (activeDraftId) {
        try {
          const existing = await getDraft(tokenResponse.accessToken, activeDraftId);
          if (cancelled) return;
          if (existing?.draft) {
            setDraft(existing.draft);
            return;
          }
        } catch {
          // Draft is gone (already generated, or expired) — fall through and
          // start a fresh one rather than dead-ending the administrator.
        }
        if (cancelled) return;
        writeActiveDraftId(null);
      }

      const data = await createDraft(tokenResponse.accessToken);
      if (cancelled) return;
      writeActiveDraftId(data.draft?.id ?? null);
      setDraft(data.draft);
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- accountKey is the stable dependency
  }, [instance, accountKey]);

  const applyWriteResult = useCallback((data) => {
    if (data.status === "generated") {
      // The draft became a story — there is nothing left to resume.
      writeActiveDraftId(null);
      setStory(data.story);
      setDraft(null);
    } else {
      setDraft(data.draft);
    }
  }, []);

  // Caught here, not by callers — StepWorldSetting/CharacterTypeList/CompletionCriteriaFields
  // all fire onPatch from a blur/change handler without awaiting it, so a rejection here
  // would otherwise become a silent unhandled promise rejection with no visible feedback
  // (e.g. a completionCriteria write missing `rule` used to fail this way with no on-screen
  // sign anything went wrong — #33 follow-up).
  const handlePatch = useCallback(
    async (updates) => {
      const fieldKey = Object.keys(updates)[0];
      try {
        const data = await patchDraft(token, draft.id, updates);
        setFieldErrors((current) => {
          if (!(fieldKey in current)) return current;
          const rest = { ...current };
          delete rest[fieldKey];
          return rest;
        });
        applyWriteResult(data);
      } catch (err) {
        setFieldErrors((current) => ({ ...current, [fieldKey]: fieldErrorMessage(err, fieldKey) }));
      }
    },
    [token, draft, applyWriteResult],
  );

  const handleSendMessage = useCallback(
    async (message) => {
      const data = await postMessage(token, draft.id, message);
      applyWriteResult(data);
    },
    [token, draft, applyWriteResult],
  );

  // The administrator's explicit "finish" action — the only thing that generates and
  // navigates away from the wizard (#33). Never triggered by a field save.
  const handleGenerate = useCallback(async () => {
    setGenerateStatus("generating");
    try {
      const data = await generateStory(token, draft.id);
      applyWriteResult(data);
      setGenerateStatus("idle");
    } catch {
      setGenerateStatus("error");
    }
  }, [token, draft, applyWriteResult]);

  if (story) {
    return (
      <div style={{ padding: "var(--space-6)" }}>
        <div style={{ fontSize: "12px", letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--color-accent-700)" }}>
          Story generated
        </div>
        <h1>{story.name || "Untitled story"}</h1>
        <p className="text-muted">Generated and saved, unpublished. Publishing is handled elsewhere.</p>
        <h3>Narrative guidance</h3>
        <p>{story.narrativeGuidance}</p>
      </div>
    );
  }

  if (!draft) {
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
      <h1>New story</h1>
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
          const status = isActive ? "In progress" : step.isDone(draft) ? "Done" : "Not started";
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
              <span style={{ fontSize: "11px", color: "var(--color-accent-700)" }}>{status}</span>
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

      <ActiveStep draft={draft} onPatch={handlePatch} onSendMessage={handleSendMessage} fieldErrors={fieldErrors} />

      <hr className="hr" style={{ margin: "32px 0 20px" }} />
      <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
        <button
          type="button"
          className="btn btn-primary"
          disabled={!isReadyToGenerate(draft) || generateStatus === "generating"}
          onClick={handleGenerate}
        >
          {generateStatus === "generating" ? "Generating…" : "Generate story"}
        </button>
        <span className="text-muted" style={{ fontSize: "13px" }}>
          {isReadyToGenerate(draft)
            ? "Ready — this saves the story and leaves the wizard."
            : "World & setting needs a world prompt, at least one character type, and at least one success condition first."}
        </span>
      </div>
      {generateStatus === "error" && (
        <div role="alert" className="text-muted" style={{ marginTop: "8px" }}>
          Could not generate the story. Please try again.
        </div>
      )}
    </div>
  );
}

export default AdminStoryWizardPage;
