/**
 * Administrator test-play screen (010-story-test-play, contracts/api.md) — starts a
 * session against a draft story's current saved configuration, reusing the same
 * presentational play components as real gameplay (research.md Decision 8). FR-011 defers
 * a visual design pass only; accessibility, semantic HTML, and design-system tokens are
 * required in full (plan.md Constitution Check).
 */
import { useMsal } from "@azure/msal-react";
import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import InstructionInput from "../components/Play/InstructionInput.jsx";
import StatusPanel from "../components/Play/StatusPanel.jsx";
import StoryPane from "../components/Play/StoryPane.jsx";
import SuggestedActions from "../components/Play/SuggestedActions.jsx";
import StoryPublishActions from "../components/Admin/StoryPublishActions.jsx";
import { getStory } from "../services/storyDraftService.js";
import { loginRequest } from "../services/msalConfig.js";
import {
  deleteTestPlaySession,
  startTestPlay,
  submitTestPlayInstruction,
} from "../services/testPlayService.js";

export function AdminStoryTestPlayPage() {
  const { storyId } = useParams();
  const navigate = useNavigate();
  const { instance, accounts: msalAccounts } = useMsal();
  const account = msalAccounts[0];
  const accountKey = account?.homeAccountId ?? account?.username ?? null;

  const [token, setToken] = useState(null);
  const [story, setStory] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [turns, setTurns] = useState([]);
  const [status, setStatus] = useState("active");
  const [completionReason, setCompletionReason] = useState(null);
  const [inputValue, setInputValue] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [notice, setNotice] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [restartOpen, setRestartOpen] = useState(false);
  const [restarting, setRestarting] = useState(false);

  const getToken = useCallback(async () => {
    const tokenResponse = await instance.acquireTokenSilent({ ...loginRequest, account });
    return tokenResponse.accessToken;
    // eslint-disable-next-line react-hooks/exhaustive-deps -- accountKey is the stable dependency
  }, [instance, accountKey]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoadError(null);
      try {
        const accessToken = await getToken();
        if (cancelled) return;
        setToken(accessToken);

        const [storyData, testPlayData] = await Promise.all([
          getStory(accessToken, storyId),
          startTestPlay(accessToken, storyId),
        ]);
        if (cancelled) return;

        setStory(storyData.story);
        setSessionId(testPlayData.sessionId);
        setTurns([{ ...testPlayData.narrative, playerInput: null }]);
      } catch (err) {
        if (!cancelled) setLoadError(err);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [getToken, accountKey, storyId]);

  const latest = turns[turns.length - 1];
  const disabled = status === "concluded" || submitting;

  const handleSubmit = async (input) => {
    setSubmitting(true);
    setNotice(null);
    try {
      const data = await submitTestPlayInstruction(token, sessionId, input);
      setTurns((prev) => [...prev, { ...data.narrative, playerInput: input }]);
      setStatus(data.status);
      setCompletionReason(data.completionReason || null);
      setInputValue("");
    } catch (err) {
      const responseStatus = err.response?.status;
      const body = err.response?.data;
      if (responseStatus === 429) {
        setNotice({ message: body?.message || "Slow down a little — take a breath before your next move." });
        setInputValue(input);
      } else if (responseStatus === 409 && body?.error === "interaction_in_progress") {
        setNotice({ message: "Your last action is still being processed. Try again." });
        setInputValue(input);
      } else if (responseStatus === 409 && body?.error === "session_concluded") {
        setStatus("concluded");
      } else {
        setNotice({ message: "Something went wrong. Please try again." });
        setInputValue(input);
      }
    } finally {
      setSubmitting(false);
    }
  };

  const openRestartDialog = () => setRestartOpen(true);
  const cancelRestart = () => setRestartOpen(false);

  const confirmRestart = async () => {
    setRestarting(true);
    try {
      if (sessionId) await deleteTestPlaySession(token, sessionId);
    } catch {
      // The abort is a best-effort cleanup — a failed delete must never block the
      // administrator from leaving (mirrors the real-play exit's own tolerance).
    } finally {
      setRestarting(false);
      navigate(`/admin/stories/${storyId}/edit`);
    }
  };

  const handleEditFromConclusion = () => navigate(`/admin/stories/${storyId}/edit`);
  const handlePublished = () => navigate("/admin");

  if (loadError) {
    return (
      <div style={{ padding: "var(--space-6)" }}>
        <p role="alert">Couldn&rsquo;t start a test-play session. Please try again.</p>
      </div>
    );
  }

  if (!story || !sessionId || !latest) {
    return (
      <div style={{ padding: "var(--space-6)" }}>
        <p className="text-muted">Starting a test session…</p>
      </div>
    );
  }

  return (
    <div className="shell" style={{ height: "100%", overflow: "hidden", display: "flex", flexDirection: "column" }}>
      <div
        style={{
          flex: "none",
          padding: "10px 40px",
          borderBottom: "2px solid var(--color-divider)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <span style={{ fontSize: "12px", letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--color-accent-700)" }}>
          Test play — draft, not published
        </span>
        <button type="button" className="btn btn-secondary" onClick={openRestartDialog}>
          Restart
        </button>
      </div>

      <div style={{ flex: 1, display: "grid", gridTemplateColumns: "1fr 292px", minHeight: 0 }}>
        <div style={{ display: "flex", flexDirection: "column", minHeight: 0, borderRight: "2px solid var(--color-divider)" }}>
          <StoryPane turns={turns} />
          <div style={{ flex: "none", borderTop: "2px solid var(--color-divider)", padding: "16px 40px 22px" }}>
            {status === "concluded" ? (
              <div>
                <h2 style={{ margin: "0 0 8px" }}>Playthrough concluded</h2>
                <p role="status" className="text-muted" style={{ margin: "0 0 18px" }}>
                  This test playthrough of &ldquo;{story.name}&rdquo; has concluded — read how it ended above.
                </p>
                <StoryPublishActions story={story} token={token} onStoryChange={setStory} onPublished={handlePublished} />
                <button
                  type="button"
                  className="btn btn-secondary"
                  style={{ marginTop: "14px" }}
                  onClick={handleEditFromConclusion}
                >
                  Return to the story wizard
                </button>
              </div>
            ) : (
              <>
                {notice && (
                  <p role="alert" className="text-muted" style={{ margin: "0 0 10px", fontSize: "13px" }}>
                    {notice.message}
                  </p>
                )}
                <SuggestedActions actions={latest.suggestedActions} onSelect={handleSubmit} disabled={disabled} />
                <InstructionInput value={inputValue} onChange={setInputValue} onSubmit={handleSubmit} disabled={disabled} />
              </>
            )}
          </div>
        </div>
        <StatusPanel
          locationLabel={latest.locationLabel}
          goalLabel={latest.goalLabel}
          progress={latest.progress}
          completionReason={completionReason}
        />
      </div>

      {restartOpen && (
        <div className="dialog-backdrop">
          <div className="dialog" role="dialog" aria-modal="true" aria-labelledby="restart-dialog-title">
            <div className="dialog-title" id="restart-dialog-title">
              Restart this test session?
            </div>
            <div className="dialog-body">
              This will abort and permanently delete the current test-play session. Your story&rsquo;s content is
              never affected.
            </div>
            <div className="dialog-actions">
              <button type="button" className="btn btn-secondary" onClick={cancelRestart} disabled={restarting}>
                Keep playing
              </button>
              <button type="button" className="btn btn-primary" onClick={confirmRestart} disabled={restarting}>
                {restarting ? "Restarting…" : "Restart"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default AdminStoryTestPlayPage;
