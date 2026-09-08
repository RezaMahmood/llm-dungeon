/**
 * 3-step adventure/character setup flow (006-adventure-and-character-setup): pick a
 * published adventure, name a character, choose a character type — in that order
 * (FR-003a) — then confirm to start play, which creates a Play Session and hands off
 * into PlayPage (008-core-gameplay-done). The header for this screen is the compact TitleBar
 * supplied by AuthenticatedLayout (FR-006 of 019-spa-refresh-button).
 */
import { useMsal } from "@azure/msal-react";
import { useCallback, useEffect, useState } from "react";

import AdventureList from "../components/GameSetup/AdventureList.jsx";
import CharacterNameStep, { MAX_CHARACTER_NAME_LENGTH } from "../components/GameSetup/CharacterNameStep.jsx";
import CharacterTypeStep from "../components/GameSetup/CharacterTypeStep.jsx";
import StoriesInProgress from "../components/GameSetup/StoriesInProgress.jsx";
import { createSession, getAdventure, getSession, listAdventures, listSavedGames, resumeSession } from "../services/gameService.js";
import { loginRequest } from "../services/msalConfig.js";
import PlayPage from "./PlayPage.jsx";

function nameError(name) {
  const trimmed = name.trim();
  if (!trimmed) return "Character name is required.";
  if (trimmed.length > MAX_CHARACTER_NAME_LENGTH) {
    return `Character name must be ${MAX_CHARACTER_NAME_LENGTH} characters or fewer.`;
  }
  return null;
}

export function GamePage() {
  const { instance, accounts } = useMsal();
  const account = accounts[0];

  const [adventures, setAdventures] = useState(null);
  const [adventuresLoading, setAdventuresLoading] = useState(true);
  const [adventuresError, setAdventuresError] = useState(null);

  const [adventureId, setAdventureId] = useState(null);
  const [characterName, setCharacterName] = useState("");
  const [characterType, setCharacterType] = useState(null);

  const [characterTypes, setCharacterTypes] = useState([]);
  const [typesLoading, setTypesLoading] = useState(false);
  const [typesError, setTypesError] = useState(null);

  const [fieldErrors, setFieldErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [session, setSession] = useState(null);

  const [savedGames, setSavedGames] = useState([]);
  const [savedGamesLoading, setSavedGamesLoading] = useState(true);
  const [savedGamesError, setSavedGamesError] = useState(null);
  const [resumeError, setResumeError] = useState(null);
  const [checkpointExitNotice, setCheckpointExitNotice] = useState(null);

  const getToken = useCallback(async () => {
    const tokenResponse = await instance.acquireTokenSilent({ ...loginRequest, account });
    return tokenResponse.accessToken;
  }, [instance, account]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setSavedGamesLoading(true);
      setSavedGamesError(null);
      try {
        const token = await getToken();
        const data = await listSavedGames(token);
        if (!cancelled) setSavedGames(data.sessions || []);
      } catch (err) {
        if (!cancelled) setSavedGamesError(err);
      } finally {
        if (!cancelled) setSavedGamesLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [getToken]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setAdventuresLoading(true);
      setAdventuresError(null);
      try {
        const token = await getToken();
        const data = await listAdventures(token);
        if (!cancelled) setAdventures(data.adventures || []);
      } catch (err) {
        if (!cancelled) setAdventuresError(err);
      } finally {
        if (!cancelled) setAdventuresLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [getToken]);

  const handleSelectAdventure = useCallback(
    (id) => {
      setAdventureId(id);
      // FR-004a: clear character type on adventure change, keep character name.
      setCharacterType(null);
      setCharacterTypes([]);
      setFieldErrors({});
      setSession(null);

      let cancelled = false;
      setTypesLoading(true);
      setTypesError(null);
      (async () => {
        try {
          const token = await getToken();
          const data = await getAdventure(token, id);
          if (!cancelled) setCharacterTypes(data.adventure?.characterTypes || []);
        } catch (err) {
          if (!cancelled) setTypesError(err);
        } finally {
          if (!cancelled) setTypesLoading(false);
        }
      })();
      return () => {
        cancelled = true;
      };
    },
    [getToken],
  );

  const handleStart = async () => {
    const clientErrors = {};
    if (!adventureId) clientErrors.adventureId = "Select an adventure.";
    const nameProblem = nameError(characterName);
    if (nameProblem) clientErrors.characterName = nameProblem;
    if (!characterType) clientErrors.characterType = "Select a character type for this adventure.";

    if (Object.keys(clientErrors).length > 0) {
      setFieldErrors(clientErrors);
      return;
    }

    setSubmitting(true);
    setFieldErrors({});
    try {
      const token = await getToken();
      const data = await createSession(token, { adventureId, characterName: characterName.trim(), characterType });
      const selectedAdventure = (adventures || []).find((a) => a.id === adventureId);
      setSession({
        sessionId: data.sessionId,
        storyName: selectedAdventure?.name || "Adventure",
        initialTurns: [data.narrative],
      });
    } catch (err) {
      if (err.response?.status === 423) {
        setFieldErrors({ adventureId: err.response.data?.message || "You're temporarily locked out. Please try again later." });
      } else {
        setFieldErrors(err.response?.data?.fields || { adventureId: "Something went wrong. Please try again." });
      }
    } finally {
      setSubmitting(false);
    }
  };

  // Only calls resume when the row isn't already the player's active game
  // (research.md Decision 5); a stale row's 409 already_active is treated as success.
  const handleResume = async (savedGame) => {
    setResumeError(null);
    try {
      const token = await getToken();
      if (!savedGame.isActiveForPlayer) {
        try {
          await resumeSession(token, savedGame.sessionId);
        } catch (err) {
          if (!(err.response?.status === 409 && err.response?.data?.error === "already_active")) {
            throw err;
          }
        }
      }
      const data = await getSession(token, savedGame.sessionId);
      setSession({
        sessionId: data.session.sessionId,
        storyName: data.session.adventureName,
        initialTurns: data.session.turns,
      });
    } catch (err) {
      // 025-story-delete FR-007/FR-008: both calls above report a story that became
      // unavailable while this row sat on screen, and each reason gets its own
      // specific message rather than the generic one below (contracts/api.md). The
      // player is already on their in-progress-games list here, so the response's
      // `promptReturnToList` needs no extra control — they are where it points.
      const responseStatus = err.response?.status;
      const body = err.response?.data;
      if (responseStatus === 404 && body?.error === "story_deleted") {
        setResumeError(body?.message || "Story has been deleted. You can no longer continue this story.");
        // The session was permanently removed along with its story (FR-004, FR-010),
        // so the row goes too rather than offering a Resume that can only fail again.
        setSavedGames((prev) => prev.filter((game) => game.sessionId !== savedGame.sessionId));
      } else if (responseStatus === 409 && body?.error === "story_unpublished") {
        setResumeError(body?.message || "Story has been unpublished. You can no longer continue this story.");
        // Unpublish never touches the session (FR-005) — the row stays, marked
        // non-continuable exactly as the next list load would render it (FR-009), and
        // reverts on its own once the story is re-published (FR-011).
        setSavedGames((prev) =>
          prev.map((game) => (game.sessionId === savedGame.sessionId ? { ...game, available: false } : game)),
        );
      } else {
        setResumeError("Couldn't resume this story. Please try again.");
      }
    }
  };

  const step1Done = Boolean(adventureId);

  if (session) {
    return (
      <PlayPage
        sessionId={session.sessionId}
        storyName={session.storyName}
        initialTurns={session.initialTurns}
        getToken={getToken}
        onExit={(checkpointFailureMessage) => {
          // PlayPage unmounts as soon as this runs, so a failed exit-save's notice
          // (FR-006a) has to be shown here, once we're back on the stories screen.
          setCheckpointExitNotice(checkpointFailureMessage || null);
          setSession(null);
        }}
      />
    );
  }

  return (
    <div style={{ maxWidth: "1020px", padding: "var(--space-6) var(--space-4) 64px" }}>
      <h1 style={{ margin: 0, fontSize: "36px" }}>Set up your game</h1>
      <hr className="hr" style={{ margin: "22px 0 32px" }} />

      <StoriesInProgress
        sessions={savedGames}
        loading={savedGamesLoading}
        error={savedGamesError}
        onResume={handleResume}
      />
      {resumeError && (
        <p role="alert" style={{ fontSize: "12px", color: "var(--color-accent-700)", margin: "8px 0 32px" }}>
          {resumeError}
        </p>
      )}
      {checkpointExitNotice && (
        <p role="status" className="text-muted" style={{ fontSize: "13px", margin: "8px 0 32px" }}>
          {checkpointExitNotice}
        </p>
      )}

      <section aria-labelledby="step1-heading" style={{ marginTop: "40px" }}>
        <h2 id="step1-heading" style={{ fontSize: "16px", margin: "0 0 12px" }}>
          01 — Choose an adventure
        </h2>
        <AdventureList
          adventures={adventures}
          loading={adventuresLoading}
          error={adventuresError}
          selectedId={adventureId}
          onSelect={handleSelectAdventure}
        />
        {fieldErrors.adventureId && (
          <p role="alert" style={{ fontSize: "12px", color: "var(--color-accent-700)", margin: "8px 0 0" }}>
            {fieldErrors.adventureId}
          </p>
        )}
      </section>

      {step1Done && (
        <section aria-labelledby="step2-heading" style={{ marginTop: "40px" }}>
          <h2 id="step2-heading" style={{ fontSize: "16px", margin: "0 0 12px" }}>
            02 — Name your character
          </h2>
          <CharacterNameStep value={characterName} onChange={setCharacterName} error={fieldErrors.characterName} />
        </section>
      )}

      {step1Done && (
        <section aria-labelledby="step3-heading" style={{ marginTop: "40px" }}>
          <h2 id="step3-heading" style={{ fontSize: "16px", margin: "0 0 12px" }}>
            03 — Choose a character type
          </h2>
          <CharacterTypeStep
            characterTypes={characterTypes}
            loading={typesLoading}
            error={typesError}
            selectedName={characterType}
            onSelect={setCharacterType}
          />
          {fieldErrors.characterType && (
            <p role="alert" style={{ fontSize: "12px", color: "var(--color-accent-700)", margin: "8px 0 0" }}>
              {fieldErrors.characterType}
            </p>
          )}
        </section>
      )}

      <div
        style={{
          marginTop: "40px",
          paddingTop: "24px",
          borderTop: "2px solid var(--color-divider)",
          display: "flex",
          alignItems: "center",
          gap: "16px",
        }}
      >
        <button type="button" className="btn btn-primary" onClick={handleStart} disabled={submitting}>
          {submitting ? "Starting…" : "Start playing"}
        </button>
      </div>
    </div>
  );
}

export default GamePage;
