import { useMsal } from "@azure/msal-react";
import { useCallback, useEffect, useState } from "react";

import StepNameCover from "../components/Admin/StoryWizard/StepNameCover.jsx";
import StepSessionLength from "../components/Admin/StoryWizard/StepSessionLength.jsx";
import StepToneReadingLevel from "../components/Admin/StoryWizard/StepToneReadingLevel.jsx";
import StepWorldSetting from "../components/Admin/StoryWizard/StepWorldSetting.jsx";
import { loginRequest } from "../services/msalConfig.js";
import { createDraft, patchDraft, postMessage } from "../services/storyDraftService.js";

const STEPS = [
  { key: "name-cover", label: "Name & cover", Component: StepNameCover },
  { key: "world-setting", label: "World & setting", Component: StepWorldSetting },
  { key: "tone-reading-level", label: "Tone & reading level", Component: StepToneReadingLevel },
  { key: "session-length", label: "Session length", Component: StepSessionLength },
];

export function AdminStoryWizardPage() {
  const { instance, accounts: msalAccounts } = useMsal();
  const account = msalAccounts[0];
  const accountKey = account?.homeAccountId ?? account?.username ?? null;

  const [token, setToken] = useState(null);
  const [draft, setDraft] = useState(null);
  const [story, setStory] = useState(null);
  const [activeStep, setActiveStep] = useState(STEPS[0].key);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const tokenResponse = await instance.acquireTokenSilent({ ...loginRequest, account });
      if (cancelled) return;
      setToken(tokenResponse.accessToken);
      const data = await createDraft(tokenResponse.accessToken);
      if (cancelled) return;
      setDraft(data.draft);
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- accountKey is the stable dependency
  }, [instance, accountKey]);

  const applyWriteResult = useCallback((data) => {
    if (data.status === "generated") {
      setStory(data.story);
      setDraft(null);
    } else {
      setDraft(data.draft);
    }
  }, []);

  const handlePatch = useCallback(
    async (updates) => {
      const data = await patchDraft(token, draft.id, updates);
      applyWriteResult(data);
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

  if (story) {
    return (
      <div style={{ padding: "var(--space-6)" }}>
        <div style={{ fontSize: "12px", letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--color-accent-700)" }}>
          Story generated
        </div>
        <h1>{story.name || "Untitled story"}</h1>
        <p className="text-muted">Saved automatically, unpublished. Publishing is handled elsewhere.</p>
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

  const ActiveStep = STEPS.find((step) => step.key === activeStep).Component;

  return (
    <div style={{ padding: "var(--space-6)" }}>
      <h1>New story</h1>
      <div className="seg" role="tablist" style={{ marginBottom: "var(--space-6)" }}>
        {STEPS.map((step) => (
          <label key={step.key} className="seg-opt" role="tab" aria-selected={activeStep === step.key}>
            <input type="radio" name="wizard-step" checked={activeStep === step.key} onChange={() => setActiveStep(step.key)} />
            <span>{step.label}</span>
          </label>
        ))}
      </div>

      <ActiveStep draft={draft} onPatch={handlePatch} onSendMessage={handleSendMessage} />
    </div>
  );
}

export default AdminStoryWizardPage;
