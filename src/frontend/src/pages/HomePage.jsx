/**
 * The post-login landing page (028-home-page-redesign, replacing MainMenu.jsx): a welcome
 * band and a two-column body pairing "Ready to play" (published stories with no session
 * for this player) and "In progress" (this player's saved sessions). Matches
 * specs/designs/07-home.html / 07-home-spec.md exactly — see that spec for layout, states,
 * and responsive rules.
 */
import { useMsal } from "@azure/msal-react";
import { useCallback, useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { usePublishRefresh } from "../context/RefreshContext.jsx";
import { useCapabilities } from "../hooks/useCapabilities.js";
import { useRefreshable } from "../hooks/useRefreshable.js";
import { listAdventures, listSavedGames } from "../services/gameService.js";
import { loginRequest } from "../services/msalConfig.js";
import "../components/Home/Home.css";
import AccessDeniedScreen from "../components/Login/AccessDeniedScreen.jsx";
import InProgressList from "../components/Home/InProgressList.jsx";
import ReadyToPlayList from "../components/Home/ReadyToPlayList.jsx";
import SessionRemovedDialog from "../components/Home/SessionRemovedDialog.jsx";
import SessionDeleteAction from "../components/Home/SessionDeleteAction.jsx";
import WelcomeBand from "../components/Home/WelcomeBand.jsx";
import PendingIndicator from "../components/Common/PendingIndicator.jsx";

export function HomePage() {
  const { instance, accounts } = useMsal();
  const account = accounts[0];
  const navigate = useNavigate();
  const location = useLocation();
  const {
    hasPlayer,
    hasAdministrator,
    loading: capabilitiesLoading,
    error: capabilitiesError,
    denied,
    refetch,
  } = useCapabilities();

  const getToken = useCallback(async () => {
    const tokenResponse = await instance.acquireTokenSilent({ ...loginRequest, account });
    return tokenResponse.accessToken;
  }, [instance, account]);

  // Starts on mount, in parallel with the capabilities check (#337): a player's stories and
  // sessions are an independent lookup from their identity/role, so gating this on
  // `hasPlayer` only bought two sequential round-trips plus a throwaway empty first fetch.
  // An account without Player capability (admin-only, pending or denied) never renders
  // either list (spec.md Edge Cases) — those branches return before `data` is read, so a
  // request that 403s here is discarded rather than shown.
  const fetchHomeData = useCallback(async () => {
    const token = await getToken();
    const [adventuresData, sessionsData] = await Promise.all([listAdventures(token), listSavedGames(token)]);
    return { adventures: adventuresData.adventures || [], sessions: sessionsData.sessions || [] };
  }, [getToken]);

  const { data, loading, error, refresh } = useRefreshable(fetchHomeData);

  const refreshAll = useCallback(() => {
    refetch();
    refresh();
  }, [refetch, refresh]);
  usePublishRefresh({ refresh: refreshAll, loading });

  // Sessions the player has deleted locally (FR-009): excluded from the fetched list with
  // no refetch. Harmless once a real refresh lands, since a genuinely deleted session is
  // already absent from the server's own response by then.
  const [locallyDeletedIds, setLocallyDeletedIds] = useState(() => new Set());
  const handleSessionDeleted = useCallback((sessionId) => {
    setLocallyDeletedIds((prev) => new Set(prev).add(sessionId));
  }, []);

  const sessions = (data?.sessions || []).filter((session) => !locallyDeletedIds.has(session.sessionId));
  const inProgressAdventureIds = new Set(sessions.map((session) => session.adventureId));
  // FR-004: a story with an active session for this player never also appears as
  // ready-to-play.
  const readyToPlay = (data?.adventures || []).filter((adventure) => !inProgressAdventureIds.has(adventure.id));

  // A one-shot signal from GamePage that the session the player was in has been deleted
  // (031-sessions-admin-design-spec FR-012/FR-013). Cleared from history on arrival so a
  // reload doesn't refire the dialog, while the dialog's own visibility lives in state.
  const [sessionRemoved, setSessionRemoved] = useState(() => Boolean(location.state?.sessionRemoved));
  // The same one-shot mechanism carries a failed exit-checkpoint's message from GamePage
  // (009-save-and-continue FR-006a): the player now leaves the game for Home directly
  // (#346), so the notice has to be shown on arrival here rather than on the screen they
  // used to be dropped back onto.
  const [checkpointExitNotice, setCheckpointExitNotice] = useState(() => location.state?.checkpointExitNotice ?? null);
  useEffect(() => {
    if (!location.state?.sessionRemoved && !location.state?.checkpointExitNotice) return;
    if (location.state.sessionRemoved) setSessionRemoved(true);
    if (location.state.checkpointExitNotice) setCheckpointExitNotice(location.state.checkpointExitNotice);
    navigate(location.pathname, { replace: true, state: null });
  }, [location.pathname, location.state, navigate]);

  const firstName = (account?.name ?? account?.username ?? "").trim().split(/\s+/)[0] || "there";

  // FR-006: Play enters the adventure's character-setup flow directly, skipping the
  // adventure-picker step GamePage used to own (research.md Decision 4).
  const handlePlay = (story) => {
    navigate("/game", { state: { adventureId: story.id } });
  };

  // FR-007: Resume hands GamePage the session id and whether it's already the player's
  // active game, so it can reuse its existing skip-the-call/409-tolerant resume sequence
  // rather than duplicating it here (research.md Decision 10).
  const handleResume = (resumedSession) => {
    if (resumedSession.available === false) return;
    navigate("/game", {
      state: { resumeSessionId: resumedSession.sessionId, isActiveForPlayer: resumedSession.isActiveForPlayer },
    });
  };

  // Account states MainMenu owned before this feature (FR-017) — Home must explain these
  // in place, never render empty story columns or a raw error.
  if (capabilitiesLoading) {
    return (
      <div className="home-shell">
        <PendingIndicator />
      </div>
    );
  }

  if (denied) {
    return <AccessDeniedScreen />;
  }

  if (capabilitiesError) {
    return (
      <div className="home-shell" style={{ padding: "var(--space-6) var(--space-4)" }}>
        <p role="alert">Something went wrong. Please try again.</p>
        <button type="button" className="btn btn-secondary" onClick={refetch}>
          Try again
        </button>
      </div>
    );
  }

  if (!hasPlayer && !hasAdministrator) {
    return (
      <div className="home-shell" style={{ padding: "var(--space-6) var(--space-4)" }}>
        <h2>Access Pending</h2>
        <p>
          Your account is registered but no roles have been assigned yet. Contact your
          administrator to grant access.
        </p>
      </div>
    );
  }

  // An administrator without Player capability can reach the admin destinations from the
  // nav, but has no player-scoped data to show here (spec.md Edge Cases) — explain in
  // place rather than rendering empty columns.
  if (!hasPlayer) {
    return (
      <div className="home-shell" style={{ padding: "var(--space-6) var(--space-4)" }}>
        <h2>No player stories here</h2>
        <p>This account only holds Administrator access. Use the nav above to manage stories or people.</p>
      </div>
    );
  }

  return (
    <div className="home-shell">
      {checkpointExitNotice && (
        <p role="status" className="text-muted" style={{ margin: 0, padding: "var(--space-4) var(--space-4) 0", fontSize: "13px" }}>
          {checkpointExitNotice}
        </p>
      )}
      <WelcomeBand firstName={firstName} inProgressCount={sessions.length} />
      <div className="home-cols">
        <ReadyToPlayList stories={readyToPlay} loading={loading} error={error} onPlay={handlePlay} />
        <InProgressList
          sessions={sessions}
          loading={loading}
          error={error}
          onResume={handleResume}
          renderDeleteAction={(session) => (
            <SessionDeleteAction session={session} token={getToken} onDeleted={handleSessionDeleted} />
          )}
        />
      </div>
      {sessionRemoved && <SessionRemovedDialog onDismiss={() => setSessionRemoved(false)} />}
    </div>
  );
}

export default HomePage;
