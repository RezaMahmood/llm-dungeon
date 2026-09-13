/**
 * The play surface (specs/designs/03-play.html, 008-core-gameplay-done) — wires session
 * creation's opening narrative and each subsequent free-text/suggested-action submit
 * into the story pane, status panel, and pause-and-exit confirmation. Also renders a
 * resumed session's whole turn history, publishes the checkpoint-save handler
 * (009-save-and-continue), and publishes the header Refresh control (029,
 * 019-spa-refresh-button).
 */
import { useCallback, useEffect, useRef, useState } from "react";

import "../components/Play/Play.css";
import InstructionInput from "../components/Play/InstructionInput.jsx";
import PauseDialog from "../components/Play/PauseDialog.jsx";
import StatusPanel from "../components/Play/StatusPanel.jsx";
import StoryPane from "../components/Play/StoryPane.jsx";
import SuggestedActions from "../components/Play/SuggestedActions.jsx";
import { usePublishPlayTitle } from "../context/PlayTitleContext.jsx";
import { usePublishRefresh } from "../context/RefreshContext.jsx";
import { getSession, resumeSession, saveCheckpoint, submitInteraction } from "../services/gameService.js";

// How long the "Checkpoint saved at …" / failure notice stays up before it clears
// itself (Constitution "Save and session behaviour" #2: "visibly and briefly").
const CHECKPOINT_NOTICE_MS = 4000;

/**
 * The session itself is gone (031-sessions-admin-design-spec FR-012). Distinct from
 * `story_deleted`, which the two shared a response with until 031 split them: a player
 * whose session was deleted under a live story must not be told their story was deleted.
 * This one never renders an in-place notice — the player leaves for Home (FR-012, D7).
 */
function isSessionRemoved(err) {
  return err.response?.status === 404 && err.response?.data?.error === "session_removed";
}

export function PlayPage({ sessionId, storyName, initialTurns, getToken, onExit, onSessionRemoved }) {
  const [turns, setTurns] = useState(() => initialTurns.map((turn) => ({ ...turn, playerInput: turn.playerInput ?? null })));
  const [status, setStatus] = useState("active");
  const [completionReason, setCompletionReason] = useState(null);
  const [inputValue, setInputValue] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [notice, setNotice] = useState(null);
  const [pauseOpen, setPauseOpen] = useState(false);
  const [checkpointNotice, setCheckpointNotice] = useState(null);
  const checkpointNoticeTimer = useRef(null);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshNotice, setRefreshNotice] = useState(null);
  // A submit and a refresh both replace `turns` wholesale from their own response —
  // if both were in flight at once, whichever resolves last would silently overwrite
  // the other's result (e.g. a refresh issued just before a submit's POST is
  // persisted server-side can return the pre-submit turn list and, resolving after the
  // submit, erase the just-added turn from view). A ref rather than state because the
  // guard must see the current value inside a callback whose own closure doesn't
  // change when `submitting`/`refreshing` do.
  const busyRef = useRef(false);

  const latest = turns[turns.length - 1];
  const locked = notice?.type === "lockout";
  const disabled = status === "concluded" || locked || submitting || refreshing;

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
    } catch (err) {
      // A removed session is not a failed save — there is nothing left to save into, and
      // "your progress is safe" would be false. The player leaves instead (FR-012).
      if (isSessionRemoved(err)) {
        onSessionRemoved?.();
        return;
      }
      setCheckpointNotice({
        type: "error",
        message: "We couldn't record that checkpoint, but your progress is safe.",
      });
    }
    if (checkpointNoticeTimer.current) clearTimeout(checkpointNoticeTimer.current);
    checkpointNoticeTimer.current = setTimeout(() => setCheckpointNotice(null), CHECKPOINT_NOTICE_MS);
  }, [getToken, sessionId, onSessionRemoved]);

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

  // Re-syncs the play screen against the session's currently recorded state (FR-009,
  // research.md Decision 3) — reuses the same getSession call GamePage's resume path
  // already makes, rather than inventing a second way to fetch this shape. `inputValue`
  // is never touched by either path (FR-010): a failure must not discard what the
  // player had already typed. Deleted/unpublished failures route into the same
  // notice branches handleSubmit's own equivalent failures already use, complete
  // with their exit action — a permanent failure with only "try again" has no path
  // out, unlike the specific case handleSubmit already covers.
  const handleRefresh = useCallback(async () => {
    if (busyRef.current) return;
    busyRef.current = true;
    setRefreshing(true);
    setRefreshNotice(null);
    try {
      const token = await getToken();
      const data = await getSession(token, sessionId);
      setTurns(data.session.turns.map((turn) => ({ ...turn, playerInput: turn.playerInput ?? null })));
      setStatus(data.session.status);
      setCompletionReason(data.session.completionReason || null);
    } catch (err) {
      const responseStatus = err.response?.status;
      const body = err.response?.data;
      if (isSessionRemoved(err)) {
        onSessionRemoved?.();
      } else if (responseStatus === 404 && body?.error === "story_deleted") {
        setNotice({
          type: "story_deleted",
          message: body?.message || "Story has been deleted. You can no longer continue this story.",
        });
      } else if (responseStatus === 409 && body?.error === "story_unpublished") {
        setNotice({
          type: "story_unpublished",
          message: body?.message || "Story has been unpublished. You can no longer continue this story.",
        });
      } else {
        setRefreshNotice({ message: "Couldn't refresh the story. Please try again." });
      }
    } finally {
      setRefreshing(false);
      busyRef.current = false;
    }
  }, [getToken, sessionId]);
  usePublishRefresh({ refresh: handleRefresh, loading: refreshing || submitting });

  const handleSubmit = async (input) => {
    if (busyRef.current) return;
    busyRef.current = true;
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
      if (isSessionRemoved(err)) {
        onSessionRemoved?.();
      } else if (responseStatus === 429) {
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
      } else if (responseStatus === 404 && body?.error === "story_deleted") {
        setNotice({
          type: "story_deleted",
          message: body?.message || "Story has been deleted. You can no longer continue this story.",
        });
      } else if (responseStatus === 409 && body?.error === "story_unpublished") {
        setNotice({
          type: "story_unpublished",
          message: body?.message || "Story has been unpublished. You can no longer continue this story.",
        });
      } else {
        setNotice({ type: "error", message: "Something went wrong. Please try again." });
        setInputValue(input);
      }
    } finally {
      setSubmitting(false);
      busyRef.current = false;
    }
  };

  const handleResume = async () => {
    try {
      const token = await getToken();
      await resumeSession(token, sessionId);
      setNotice(null);
    } catch (err) {
      if (isSessionRemoved(err)) {
        onSessionRemoved?.();
        return;
      }
      setNotice({ type: "error", message: "Couldn't resume this story. Please try again." });
    }
  };

  return (
    <div className="play-shell">
      <div className="play-body">
        <div className="play-main">
          <div style={{ display: "flex", flexDirection: "column", minHeight: 0, borderRight: "2px solid var(--color-divider)" }}>
            <StoryPane turns={turns} />
            <div className="play-dock">
              {checkpointNotice && (
                <p role={checkpointNotice.type === "error" ? "alert" : "status"} className="text-muted play-notice">
                  {checkpointNotice.message}
                </p>
              )}
              {refreshNotice && (
                <p role="alert" className="text-muted play-notice">
                  {refreshNotice.message}
                </p>
              )}
              {status === "concluded" ? (
                <p className="text-muted" role="status">
                  This story has ended.
                </p>
              ) : notice?.type === "session_inactive" ? (
                <div>
                  <p role="alert" className="text-muted play-notice">
                    {notice.message}
                  </p>
                  <button type="button" className="btn btn-primary" onClick={handleResume}>
                    Resume this story
                  </button>
                </div>
              ) : notice?.type === "story_deleted" || notice?.type === "story_unpublished" ? (
                <div>
                  <p role="alert" className="text-muted play-notice">
                    {notice.message}
                  </p>
                  <button type="button" className="btn btn-primary" onClick={() => onExit()}>
                    Return to your story list
                  </button>
                </div>
              ) : (
                <>
                  {notice && (
                    <p role="alert" className="text-muted play-notice">
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
