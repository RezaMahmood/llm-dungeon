/**
 * The play surface (specs/designs/03-play.html, 008-core-gameplay) — wires session
 * creation's opening narrative and each subsequent free-text/suggested-action submit
 * into the story pane, status panel, and pause-and-exit confirmation.
 */
import { useState } from "react";

import InstructionInput from "../components/Play/InstructionInput.jsx";
import PauseDialog from "../components/Play/PauseDialog.jsx";
import StatusPanel from "../components/Play/StatusPanel.jsx";
import StoryPane from "../components/Play/StoryPane.jsx";
import SuggestedActions from "../components/Play/SuggestedActions.jsx";
import { resumeSession, submitInteraction } from "../services/gameService.js";

export function PlayPage({ sessionId, storyName, initialNarrative, getToken, onExit }) {
  const [turns, setTurns] = useState([{ ...initialNarrative, playerInput: null }]);
  const [status, setStatus] = useState("active");
  const [completionReason, setCompletionReason] = useState(null);
  const [inputValue, setInputValue] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [notice, setNotice] = useState(null);
  const [pauseOpen, setPauseOpen] = useState(false);

  const latest = turns[turns.length - 1];
  const locked = notice?.type === "lockout";
  const disabled = status === "concluded" || locked || submitting;

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
    <div className="shell" style={{ height: "100vh", overflow: "hidden", display: "flex", flexDirection: "column" }}>
      <div style={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 0, position: "relative" }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "16px",
            padding: "12px 20px",
            borderBottom: "2px solid var(--color-divider)",
            flex: "none",
          }}
        >
          <span style={{ fontFamily: "var(--font-heading)", fontWeight: 800, fontSize: "17px", marginRight: "auto" }}>
            {storyName}
          </span>
          <span className="text-muted" style={{ fontSize: "12px" }}>
            Autosaved after every turn
          </span>
          <button className="btn btn-primary" type="button" onClick={() => setPauseOpen(true)}>
            Pause &amp; exit
          </button>
        </div>

        <div style={{ flex: 1, display: "grid", gridTemplateColumns: "1fr 292px", minHeight: 0 }}>
          <div style={{ display: "flex", flexDirection: "column", minHeight: 0, borderRight: "2px solid var(--color-divider)" }}>
            <StoryPane turns={turns} />
            <div style={{ flex: "none", borderTop: "2px solid var(--color-divider)", padding: "16px 40px 22px" }}>
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
        <PauseDialog locationLabel={latest.locationLabel} onKeepPlaying={() => setPauseOpen(false)} onConfirmExit={onExit} />
      )}
    </div>
  );
}

export default PlayPage;
