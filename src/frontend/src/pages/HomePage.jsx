/**
 * The post-login landing page (028-home-page-redesign, replacing MainMenu.jsx): a welcome
 * band and a two-column body pairing "Ready to play" (published stories with no session
 * for this player) and "In progress" (this player's saved sessions). Matches
 * specs/designs/07-home.html / 07-home-spec.md exactly — see that spec for layout, states,
 * and responsive rules.
 */
import { useMsal } from "@azure/msal-react";
import { useCallback } from "react";
import { useNavigate } from "react-router-dom";

import { usePublishRefresh } from "../context/RefreshContext.jsx";
import { useCapabilities } from "../hooks/useCapabilities.js";
import { useRefreshable } from "../hooks/useRefreshable.js";
import { listAdventures, listSavedGames } from "../services/gameService.js";
import { loginRequest } from "../services/msalConfig.js";
import "../components/Home/Home.css";
import AccessDeniedScreen from "../components/Login/AccessDeniedScreen.jsx";
import InProgressList from "../components/Home/InProgressList.jsx";
import ReadyToPlayList from "../components/Home/ReadyToPlayList.jsx";
import WelcomeBand from "../components/Home/WelcomeBand.jsx";

export function HomePage() {
  const { instance, accounts } = useMsal();
  const account = accounts[0];
  const navigate = useNavigate();
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

  // An account without Player capability (admin-only) is never served either list
  // (spec.md Edge Cases) — HomePage's caller handles that state before this data matters,
  // so this simply avoids an API call that would only 403.
  const fetchHomeData = useCallback(async () => {
    if (!hasPlayer) return { adventures: [], sessions: [] };
    const token = await getToken();
    const [adventuresData, sessionsData] = await Promise.all([listAdventures(token), listSavedGames(token)]);
    return { adventures: adventuresData.adventures || [], sessions: sessionsData.sessions || [] };
  }, [getToken, hasPlayer]);

  const { data, loading, error, refresh } = useRefreshable(fetchHomeData);

  const refreshAll = useCallback(() => {
    refetch();
    refresh();
  }, [refetch, refresh]);
  usePublishRefresh({ refresh: refreshAll, loading });

  const sessions = data?.sessions || [];
  const inProgressAdventureIds = new Set(sessions.map((session) => session.adventureId));
  // FR-004: a story with an active session for this player never also appears as
  // ready-to-play.
  const readyToPlay = (data?.adventures || []).filter((adventure) => !inProgressAdventureIds.has(adventure.id));

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
    return <div className="home-shell">Loading…</div>;
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
      <WelcomeBand firstName={firstName} inProgressCount={sessions.length} />
      <div className="home-cols">
        <ReadyToPlayList stories={readyToPlay} loading={loading} error={error} onPlay={handlePlay} />
        <InProgressList sessions={sessions} loading={loading} error={error} onResume={handleResume} />
      </div>
    </div>
  );
}

export default HomePage;
