/**
 * The play surface (specs/designs/03-play.html, 008-core-gameplay) — wires session
 * creation's opening narrative and each subsequent free-text/suggested-action submit
 * into the story pane, status panel, and pause-and-exit confirmation. Also renders a
 * resumed session's whole turn history and publishes the checkpoint-save handler
 * (009-save-and-continue).
 */
import { useCallback, useEffect, useRef, useState } from "react";

import InstructionInput from "../components/Play/InstructionInput.jsx";
import PauseDialog from "../components/Play/PauseDialog.jsx";
import StatusPanel from "../components/Play/StatusPanel.jsx";
import StoryPane from "../components/Play/StoryPane.jsx";
import SuggestedActions from "../components/Play/SuggestedActions.jsx";
import { usePublishPlayTitle } from "../context/PlayTitleContext.jsx";
import { resumeSession, saveCheckpoint, submitInteraction } from "../services/gameService.js";

// How long the "Checkpoint saved at …" / failure notice stays up before it clears
// itself (Constitution "Save and session behaviour" #2: "visibly and briefly").
const CHECKPOINT_NOTICE_MS = 4000;

export function PlayPage({ sessionId, storyName, initialTurns, getToken, onExit }) {
  const [turns, setTurns] = useState(() => initialTurns.map((turn) => ({ ...turn, playerInput: turn.playerInput ?? null })));
  const [status, setStatus] = useState("active");
  const [completionReason, setCompletionReason] = useState(null);
  const [inputValue, setInputValue] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [notice, setNotice] = useState(null);
  const [pauseOpen, setPauseOpen] = useState(false);
  const [checkpointNotice, setCheckpointNotice] = useState(null);
  const checkpointNoticeTimer = useRef(null);

  const latest = turns[turns.length - 1];
  const locked = notice?.type === "lockout";
  const disabled = status === "concluded" || locked || submitting;

  useEffect(
    () => () => {
      if (checkpointNoticeTimer.current) clearTimeout(checkpointNoticeTimer.current);
    },
    [],
  );

  const handleSaveCheckpoint = useCallback(async () => {
    try {
      const token = await getToken();
      const data = await saveCheckpoint(token, sessionId);
      setCheckpointNotice({ type: "success", message: `Checkpoint saved at ${data.checkpoint.label}` });
    } catch {
      setCheckpointNotice({
        type: "error",
        message: "We couldn't record that checkpoint, but your progress is safe.",
      });
    }
    if (checkpointNoticeTimer.current) clearTimeout(checkpointNoticeTimer.current);
    checkpointNoticeTimer.current = setTimeout(() => setCheckpointNotice(null), CHECKPOINT_NOTICE_MS);
  }, [getToken, sessionId]);

  // A failed save must never block, delay, or reverse departure (FR-006a) — the
  // checkpoint call is best-effort and `onExit` always runs.
  const handleConfirmExit = useCallback(async () => {
    // The turns themselves are already persisted; only the marker can be lost. FR-006a
    // still requires telling the player, so a failure is passed along to `onExit` —
    // this page unmounts immediately after, so it cannot show the notice itself.
    try {
      const token = await getToken();
      await saveCheckpoint(token, sessionId);
      onExit();
    } catch {
      onExit("We couldn't record that checkpoint, but your progress is safe.");
    }
  }, [getToken, sessionId, onExit]);

  // Published to the header AuthenticatedLayout renders, so this page never grows a
  // second title bar with its own, unconfirmed way out (FR-016).
  const openPauseDialog = useCallback(() => setPauseOpen(true), []);
  usePublishPlayTitle({ storyTitle: storyName, onPauseExit: openPauseDialog, onSaveCheckpoint: handleSaveCheckpoint });

  const handleSubmit = async (input) => {
    setSubmitting(true);
    setNotice(null);
    try {
      const token = await getToken();
      const data = await submitInteraction(token, sessionId, input);
      setTurns((prev) => [...prev, { ...data.narrative, playerInput: input }]);
      setStatus(data.status);
      setCompletionReason(data.completionReason || null);
      setInputValue("");
    } catch (err) {
      const responseStatus = err.response?.status;
      const body = err.response?.data;
      if (responseStatus === 429) {
        setNotice({ type: "rate_limited", message: body?.message || "Slow down a little." });
        setInputValue(input);
      } else if (responseStatus === 409 && body?.error === "interaction_in_progress") {
        setNotice({ type: "interaction_in_progress", message: "Your last action is still being processed. Try again." });
        setInputValue(input);
      } else if (responseStatus === 409 && body?.error === "session_inactive") {
        setNotice({ type: "session_inactive", message: body?.message || "You left this story to play another." });
      } else if (responseStatus === 423) {
        setNotice({ type: "lockout", message: body?.message || "You're temporarily locked out." });
      } else if (responseStatus === 409 && body?.error === "session_concluded") {
        setStatus("concluded");
      } else {
        setNotice({ type: "error", message: "Something went wrong. Please try again." });
        setInputValue(input);
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleResume = async () => {
    try {
      const token = await getToken();
      await resumeSession(token, sessionId);
      setNotice(null);
    } catch {
      setNotice({ type: "error", message: "Couldn't resume this story. Please try again." });
    }
  };

  return (
    <div className="shell" style={{ height: "100%", overflow: "hidden", display: "flex", flexDirection: "column" }}>
      <div style={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 0, position: "relative" }}>
        <div style={{ flex: 1, display: "grid", gridTemplateColumns: "1fr 292px", minHeight: 0 }}>
          <div style={{ display: "flex", flexDirection: "column", minHeight: 0, borderRight: "2px solid var(--color-divider)" }}>
            <StoryPane turns={turns} />
            <div style={{ flex: "none", borderTop: "2px solid var(--color-divider)", padding: "16px 40px 22px" }}>
              {checkpointNotice && (
                <p
                  role={checkpointNotice.type === "error" ? "alert" : "status"}
                  className="text-muted"
                  style={{ margin: "0 0 10px", fontSize: "13px" }}
                >
                  {checkpointNotice.message}
                </p>
              )}
              {status === "concluded" ? (
                <p className="text-muted" role="status">
                  This story has ended.
                </p>
              ) : notice?.type === "session_inactive" ? (
                <div>
                  <p role="alert" className="text-muted" style={{ margin: "0 0 10px" }}>
                    {notice.message}
                  </p>
                  <button type="button" className="btn btn-primary" onClick={handleResume}>
                    Resume this story
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
      </div>

      {pauseOpen && (
        <PauseDialog locationLabel={latest.locationLabel} onKeepPlaying={() => setPauseOpen(false)} onConfirmExit={handleConfirmExit} />
      )}
    </div>
  );
}

export default PlayPage;
