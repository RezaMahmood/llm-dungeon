import { useMsal } from "@azure/msal-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";

import StepNameCover from "../components/Admin/StoryWizard/StepNameCover.jsx";
import StepPublish from "../components/Admin/StoryWizard/StepPublish.jsx";
import StepSessionLength from "../components/Admin/StoryWizard/StepSessionLength.jsx";
import StepToneReadingLevel from "../components/Admin/StoryWizard/StepToneReadingLevel.jsx";
import StepWorldSetting from "../components/Admin/StoryWizard/StepWorldSetting.jsx";
import PendingButton from "../components/Common/PendingButton.jsx";
import PendingIndicator from "../components/Common/PendingIndicator.jsx";
import { usePublishRefresh } from "../context/RefreshContext.jsx";
import { useUnsavedChangesWarning } from "../hooks/useUnsavedChangesWarning.js";
import { loginRequest } from "../services/msalConfig.js";
import {
  createDraft,
  createEditDraft,
  generateStory,
  getDraft,
  patchDraft,
  saveDraftToStory,
  suggestWorldPrompt,
} from "../services/storyDraftService.js";

const STALE_STORY_MESSAGE = "This story changed since you opened it. Reload it and reapply your change.";

// Which draft this browser session is currently building. Without this, leaving
// the wizard via the nav bar and coming back would start a brand-new blank
// draft, stranding work the server had already saved (FR-005, SC-003).
const ACTIVE_DRAFT_KEY = "llmdungeon.storyWizard.activeDraftId";

// A draft expires server-side 24h after its last write (DRAFT_TTL_SECONDS in
// backend/models/story_draft.py, reset by every draft write). The remembered id is
// stamped with the time of the write that produced it, so a resume the server can only
// answer with 404 is dropped here instead of being spent as a request — an expected
// "nothing to resume" state should never reach the administrator's console as a failed
// request (#135). The stamp slides with the server's TTL because every successful write
// re-stamps it, exactly as every write resets `ttl` on the document.
const DRAFT_TTL_MS = 24 * 60 * 60 * 1000;

function readActiveDraftId() {
  try {
    const raw = sessionStorage.getItem(ACTIVE_DRAFT_KEY);
    if (!raw) return null;
    let record = null;
    try {
      record = JSON.parse(raw);
    } catch {
      // Written by a build that stored the bare id: its age is unknowable, so it can
      // only be guessed at with a request that may 404. Drop it instead.
      record = null;
    }
    if (!record || typeof record !== "object" || !record.id || typeof record.savedAt !== "number") {
      writeActiveDraftId(null);
      return null;
    }
    if (Date.now() - record.savedAt >= DRAFT_TTL_MS) {
      writeActiveDraftId(null);
      return null;
    }
    return record.id;
  } catch {
    return null;
  }
}

function writeActiveDraftId(draftId) {
  try {
    if (draftId) {
      sessionStorage.setItem(ACTIVE_DRAFT_KEY, JSON.stringify({ id: draftId, savedAt: Date.now() }));
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
  // An expired or rejected sign-in is not a problem with what was typed, so it must not
  // be reported in the field's own words — it needs the administrator to sign in again
  // (#137).
  const status = err?.response?.status;
  if (status === 401 || status === 403) {
    return "Your sign-in has expired. Reload the page to sign in again, then save.";
  }
  const backendMessage = err?.response?.data?.message;
  if (!backendMessage) return "Could not save this — please try again.";
  const prefix = `${fieldKey}: `;
  const reason = backendMessage.startsWith(prefix) ? backendMessage.slice(prefix.length) : backendMessage;
  return reason.charAt(0).toUpperCase() + reason.slice(1);
}

// World & Setting's own fields (worldPrompt, characterTypes, completionCriteria) — used
// for that step tab's own "Done" status, separate from the overall generate gate below,
// which also requires a story name from the Name & cover step.
function isWorldSettingComplete(draft) {
  return (
    Boolean(draft.worldPrompt) &&
    (draft.characterTypes?.length ?? 0) > 0 &&
    (draft.completionCriteria?.successConditions?.length ?? 0) > 0
  );
}

// The Completeness Rule (data-model.md) — mirrors StoryDraft.is_complete() on the
// backend, so the wizard can tell the administrator generation is possible without
// waiting on a round trip. Filling this in never generates or navigates by itself
// (#33) — only the explicit "Generate story" action does. A story name is required
// (revised 2026-08-31) — narrative content alone isn't enough to generate a story.
function missingRequirements(draft) {
  const missing = [];
  if (!draft.name) missing.push("a story name (Name & cover)");
  if (!draft.worldPrompt) missing.push("a world prompt");
  if (!(draft.characterTypes?.length > 0)) missing.push("at least one character type");
  if (!(draft.completionCriteria?.successConditions?.length > 0)) missing.push("at least one success condition");
  return missing;
}

function isReadyToGenerate(draft) {
  return missingRequirements(draft).length === 0;
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
    isDone: isWorldSettingComplete,
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
  const { storyId } = useParams();
  const isEditMode = Boolean(storyId);
  const { instance, accounts: msalAccounts } = useMsal();
  const account = msalAccounts[0];
  const accountKey = account?.homeAccountId ?? account?.username ?? null;

  const [draft, setDraft] = useState(null);
  const [story, setStory] = useState(null);
  const [activeStep, setActiveStep] = useState(STEPS[0].key);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshError, setRefreshError] = useState(null);
  const [isDirty, setIsDirty] = useState(false);
  const refreshingRef = useRef(false);
  const [generateStatus, setGenerateStatus] = useState("idle"); // idle | generating | error | stale
  const [fieldErrors, setFieldErrors] = useState({}); // { [fieldKey]: message }
  const [loadError, setLoadError] = useState(null);
  // Blur-saved fields (world setting, character types, completion criteria) write to the
  // server without any control of their own to grey out, so the wizard counts what is in
  // flight and says so once, in one place (issue #347). A count, not a boolean: leaving a
  // field can start a second write while the first is still out. Steps with their own Save
  // button pass `quiet` — that button already spins, and a second "Saving…" beneath it
  // would say the same thing twice.
  const [pendingWrites, setPendingWrites] = useState(0);

  useUnsavedChangesWarning(isDirty);

  // Resolved lazily, per call, rather than acquired once on mount and kept in state —
  // the wizard is a long-lived screen, and a token acquired when it opened can easily
  // have expired by the time the administrator saves a field, which the backend
  // correctly rejects with a 401 (#137). Same idiom as AdminPage's own `getToken`.
  const getToken = useCallback(async () => {
    const tokenResponse = await instance.acquireTokenSilent({ ...loginRequest, account });
    return tokenResponse.accessToken;
    // eslint-disable-next-line react-hooks/exhaustive-deps -- accountKey is the stable dependency
  }, [instance, accountKey]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const accessToken = await getToken();
      if (cancelled) return;

      // Edit mode (FR-003): open a fresh edit draft seeded from the story every time
      // this route is entered — there is nothing to resume from sessionStorage, since
      // the draft is bound to `storyId`, not to this browser session.
      if (isEditMode) {
        const data = await createEditDraft(accessToken, storyId);
        if (cancelled) return;
        setDraft(data.draft);
        return;
      }

      // Resume the draft this session was already building, so navigating away
      // via the nav bar and back does not discard saved progress (FR-005).
      const activeDraftId = readActiveDraftId();
      if (activeDraftId) {
        try {
          const existing = await getDraft(accessToken, activeDraftId);
          if (cancelled) return;
          if (existing?.draft) {
            setDraft(existing.draft);
            return;
          }
        } catch (err) {
          if (cancelled) return;
          // Only the server saying the draft is gone (already generated, or expired)
          // justifies forgetting it and starting over. Any other failure — offline, a
          // 401, a 5xx — says nothing about whether the draft still exists, and
          // starting a fresh one there would strand work the administrator had saved.
          const status = err?.response?.status;
          if (status !== 404 && status !== 410) {
            setLoadError(err);
            return;
          }
        }
        if (cancelled) return;
        writeActiveDraftId(null);
      }

      const data = await createDraft(accessToken);
      // Recorded before the cancellation check: the draft exists on the server either
      // way, so a wizard that unmounted mid-create must still be able to resume it
      // rather than abandon it and create another.
      writeActiveDraftId(data.draft?.id ?? null);
      if (cancelled) return;
      setDraft(data.draft);
    })();
    return () => {
      cancelled = true;
    };
  }, [getToken, isEditMode, storyId]);

  const applyWriteResult = useCallback(
    (data) => {
      if (data.status === "generated" || data.status === "saved") {
        // The draft became (or was applied back to) a story — there is nothing left to resume.
        writeActiveDraftId(null);
        setStory(data.story);
        setDraft(null);
      } else {
        // Every draft write resets the document's server-side TTL, so re-stamp the
        // remembered id to keep the client's idea of when it expires in step with the
        // server's. Edit drafts are bound to a storyId and are never resumed from
        // session storage, so they are deliberately not recorded here.
        if (!isEditMode && data.draft?.id) writeActiveDraftId(data.draft.id);
        setDraft(data.draft);
      }
    },
    [isEditMode],
  );

  // Caught here, not by callers — StepWorldSetting/CharacterTypeList/CompletionCriteriaFields
  // all fire onPatch from a blur/change handler without awaiting it, so a rejection here
  // would otherwise become a silent unhandled promise rejection with no visible feedback
  // (e.g. a completionCriteria write missing `rule` used to fail this way with no on-screen
  // sign anything went wrong — #33 follow-up).
  // Returns whether the write actually landed, so a step that offers its own explicit
  // Save can confirm only a real save — reporting "Saved" for a write the server refused
  // is how an administrator loses work without knowing it (#137). Callers that fire and
  // forget can keep ignoring the result.
  const handlePatch = useCallback(
    async (updates, { quiet = false } = {}) => {
      const fieldKey = Object.keys(updates)[0];
      if (!quiet) setPendingWrites((n) => n + 1);
      try {
        const data = await patchDraft(await getToken(), draft.id, updates);
        setFieldErrors((current) => {
          if (!(fieldKey in current)) return current;
          const rest = { ...current };
          delete rest[fieldKey];
          return rest;
        });
        applyWriteResult(data);
        return true;
      } catch (err) {
        setFieldErrors((current) => ({ ...current, [fieldKey]: fieldErrorMessage(err, fieldKey) }));
        return false;
      } finally {
        if (!quiet) setPendingWrites((n) => n - 1);
      }
    },
    [getToken, draft, applyWriteResult],
  );

  // A single pass over the administrator's idea (#227) — the returned draft's worldPrompt
  // is the whole result, so it flows through the same write path as any other field write.
  const handleSuggestWorldPrompt = useCallback(
    async (idea) => {
      const data = await suggestWorldPrompt(await getToken(), draft.id, idea);
      applyWriteResult(data);
    },
    [getToken, draft, applyWriteResult],
  );

  // Re-fetches the draft currently being edited without touching activeStep
  // or restarting the resume/create-new-draft flow above (FR-003).
  const refreshDraft = useCallback(async () => {
    if (!draft?.id || refreshingRef.current) return;
    refreshingRef.current = true;
    setRefreshing(true);
    setRefreshError(null);
    try {
      const existing = await getDraft(await getToken(), draft.id);
      if (existing?.draft) {
        setDraft(existing.draft);
      }
    } catch (err) {
      setRefreshError(err);
    } finally {
      refreshingRef.current = false;
      setRefreshing(false);
    }
  }, [getToken, draft?.id]);

  usePublishRefresh({ refresh: refreshDraft, loading: refreshing });

  // The administrator's explicit "finish" action — the only thing that generates and
  // navigates away from the wizard (#33). Never triggered by a field save.
  const handleGenerate = useCallback(async () => {
    setGenerateStatus("generating");
    try {
      const data = await generateStory(await getToken(), draft.id);
      applyWriteResult(data);
      setGenerateStatus("idle");
    } catch {
      setGenerateStatus("error");
    }
  }, [getToken, draft, applyWriteResult]);

  // Edit mode's terminal action (FR-003, FR-006): applies the draft back to its source
  // story. A stale save (FR-006) shows the reload-and-reapply message instead of a
  // generic error, since the fix is specific — reload the story and reapply the change.
  const handleSaveChanges = useCallback(async () => {
    setGenerateStatus("generating");
    try {
      const data = await saveDraftToStory(await getToken(), draft.id);
      applyWriteResult(data);
      setGenerateStatus("idle");
    } catch (err) {
      setGenerateStatus(err?.response?.status === 409 ? "stale" : "error");
    }
  }, [getToken, draft, applyWriteResult]);

  if (story) {
    return (
      <div style={{ padding: "var(--space-6)" }}>
        <div style={{ fontSize: "12px", letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--color-accent-700)" }}>
          {isEditMode ? "Story saved" : "Story generated"}
        </div>
        <h1>{story.name || "Untitled story"}</h1>
        <p className="text-muted">{isEditMode ? "Changes saved." : "Generated and saved."}</p>
        <h3>Narrative guidance</h3>
        <p>{story.narrativeGuidance}</p>

        {story.startingPoint && (
          <>
            <h3>Opening scene</h3>
            <p>{story.startingPoint.narrativeText}</p>
            <p className="text-muted">Every player starts here — download the configuration file to edit it.</p>
          </>
        )}

        <hr className="hr" style={{ margin: "24px 0" }} />
        <h3>Test play</h3>
        <p className="text-muted">Play through this draft before publishing it.</p>
        <Link className="btn btn-secondary" to={`/admin/stories/${story.id}/test-play`}>
          Start test play
        </Link>

        <hr className="hr" style={{ margin: "24px 0" }} />
        <h3>Publish & assign</h3>
        <StepPublish story={story} token={getToken} onStoryChange={setStory} />
      </div>
    );
  }

  if (loadError) {
    return (
      <div style={{ padding: "var(--space-6)" }}>
        <p role="alert">
          Couldn&rsquo;t open your story draft. Your saved progress is still there &mdash; reload the page to try again.
        </p>
      </div>
    );
  }

  if (!draft) {
    return (
      <div style={{ padding: "var(--space-6)" }}>
        <PendingIndicator>{isEditMode ? "Loading story…" : "Starting a new story…"}</PendingIndicator>
      </div>
    );
  }

  const activeStepConfig = STEPS.find((step) => step.key === activeStep);
  const ActiveStep = activeStepConfig.Component;

  return (
    <div style={{ maxWidth: "1080px", padding: "var(--space-6) var(--space-4) 64px" }}>
      <h1>{isEditMode ? "Edit story" : "New story"}</h1>
      {refreshError && (
        <p role="alert" className="text-muted">
          Couldn&rsquo;t refresh the draft. Showing the last loaded version.
        </p>
      )}
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

      <ActiveStep
        draft={draft}
        onPatch={handlePatch}
        onSuggestWorldPrompt={handleSuggestWorldPrompt}
        onDirtyChange={setIsDirty}
        fieldErrors={fieldErrors}
      />

      {pendingWrites > 0 && (
        <PendingIndicator style={{ marginTop: "16px", fontSize: "13px" }}>Saving…</PendingIndicator>
      )}

      <hr className="hr" style={{ margin: "32px 0 20px" }} />
      <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
        <PendingButton
          className="btn btn-primary"
          disabled={!isReadyToGenerate(draft)}
          pending={generateStatus === "generating"}
          pendingLabel={isEditMode ? "Saving…" : "Generating…"}
          onClick={isEditMode ? handleSaveChanges : handleGenerate}
        >
          {isEditMode ? "Save changes" : "Generate story"}
        </PendingButton>
        <span className="text-muted" style={{ fontSize: "13px" }}>
          {isReadyToGenerate(draft)
            ? isEditMode
              ? "Ready — this saves your changes to the story."
              : "Ready — this saves the story and leaves the wizard."
            : `Still needs ${missingRequirements(draft).join(", ")}.`}
        </span>
      </div>
      {generateStatus === "error" && (
        <div role="alert" className="text-muted" style={{ marginTop: "8px" }}>
          {isEditMode ? "Could not save this story. Please try again." : "Could not generate the story. Please try again."}
        </div>
      )}
      {generateStatus === "stale" && (
        <div role="alert" className="text-muted" style={{ marginTop: "8px" }}>
          {STALE_STORY_MESSAGE}
        </div>
      )}
    </div>
  );
}

export default AdminStoryWizardPage;
