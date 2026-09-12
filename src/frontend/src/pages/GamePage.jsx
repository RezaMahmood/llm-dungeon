/**
 * Character setup for a single, already-chosen adventure, or a direct resume — both
 * entered only via route state handed in by HomePage's Play/Resume actions
 * (028-home-page-redesign, research.md Decision 10; supersedes this page's own former
 * adventure-picker/in-progress list, now owned by Home). Renders the compact TitleBar
 * supplied by AuthenticatedLayout (FR-006 of 019-spa-refresh-button).
 */
import { useMsal } from "@azure/msal-react";
import { useCallback, useEffect, useState } from "react";
import { Link, Navigate, useLocation } from "react-router-dom";

import CharacterNameStep, { MAX_CHARACTER_NAME_LENGTH } from "../components/GameSetup/CharacterNameStep.jsx";
import CharacterTypeStep from "../components/GameSetup/CharacterTypeStep.jsx";
import { createSession, getAdventure, getSession, resumeSession } from "../services/gameService.js";
import { loginRequest } from "../services/msalConfig.js";
import PlayPage from "./PlayPage.jsx";

/** The one outer gutter this whole page uses, at every stage (setup form, resuming
 * spinner, resume-error screen) — factored out after `/code-review high` flagged the
 * inline style object as copy-pasted verbatim across three separate returns below. */
function PageContainer({ children }) {
  return <div style={{ maxWidth: "1020px", padding: "var(--space-6) var(--space-4) 64px" }}>{children}</div>;
}

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
  const { state } = useLocation();
  const { adventureId, resumeSessionId, isActiveForPlayer } = state || {};

  const [characterName, setCharacterName] = useState("");
  const [characterType, setCharacterType] = useState(null);
  const [characterTypes, setCharacterTypes] = useState([]);
  const [adventureName, setAdventureName] = useState(null);
  const [typesLoading, setTypesLoading] = useState(Boolean(adventureId));
  const [typesError, setTypesError] = useState(null);

  const [fieldErrors, setFieldErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [session, setSession] = useState(null);

  const [resuming, setResuming] = useState(Boolean(resumeSessionId));
  const [resumeError, setResumeError] = useState(null);
  const [checkpointExitNotice, setCheckpointExitNotice] = useState(null);

  const getToken = useCallback(async () => {
    const tokenResponse = await instance.acquireTokenSilent({ ...loginRequest, account });
    return tokenResponse.accessToken;
  }, [instance, account]);

  // Character-setup path: Home already chose the adventure (FR-006) — this only needs
  // that adventure's character types and display name.
  useEffect(() => {
    if (!adventureId) return;
    let cancelled = false;
    setTypesLoading(true);
    setTypesError(null);
    (async () => {
      try {
        const token = await getToken();
        const data = await getAdventure(token, adventureId);
        if (!cancelled) {
          setCharacterTypes(data.adventure?.characterTypes || []);
          setAdventureName(data.adventure?.name || null);
        }
      } catch (err) {
        if (!cancelled) setTypesError(err);
      } finally {
        if (!cancelled) setTypesLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [adventureId, getToken]);

  // Resume path: Home already knows whether this is the player's active game
  // (research.md Decision 10) — the same skip-the-call/409-tolerant/story-unavailable
  // handling GamePage always had, just triggered by route state instead of a click.
  useEffect(() => {
    if (!resumeSessionId) return;
    let cancelled = false;
    (async () => {
      try {
        const token = await getToken();
        if (!isActiveForPlayer) {
          try {
            await resumeSession(token, resumeSessionId);
          } catch (err) {
            if (!(err.response?.status === 409 && err.response?.data?.error === "already_active")) {
              throw err;
            }
          }
        }
        const data = await getSession(token, resumeSessionId);
        if (!cancelled) {
          setSession({
            sessionId: data.session.sessionId,
            storyName: data.session.adventureName,
            initialTurns: data.session.turns,
          });
        }
      } catch (err) {
        if (cancelled) return;
        // 025-story-delete-done FR-007/FR-008: each reason gets its own specific
        // message rather than a generic one.
        const responseStatus = err.response?.status;
        const body = err.response?.data;
        if (responseStatus === 404 && body?.error === "story_deleted") {
          setResumeError(body?.message || "Story has been deleted. You can no longer continue this story.");
        } else if (responseStatus === 409 && body?.error === "story_unpublished") {
          setResumeError(body?.message || "Story has been unpublished. You can no longer continue this story.");
        } else {
          setResumeError("Couldn't resume this story. Please try again.");
        }
      } finally {
        if (!cancelled) setResuming(false);
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- runs once for the id Home handed in via route state
  }, []);

  const handleStart = async () => {
    const clientErrors = {};
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
      setSession({
        sessionId: data.sessionId,
        storyName: adventureName || "Adventure",
        initialTurns: [data.narrative],
      });
    } catch (err) {
      if (err.response?.status === 423) {
        setFieldErrors({ characterType: err.response.data?.message || "You're temporarily locked out. Please try again later." });
      } else {
        setFieldErrors(err.response?.data?.fields || { characterType: "Something went wrong. Please try again." });
      }
    } finally {
      setSubmitting(false);
    }
  };

  // Reached with no route state (e.g. a stale bookmark/back navigation) — Home is the
  // only entry point into this flow (research.md Decision 10).
  if (!adventureId && !resumeSessionId) {
    return <Navigate to="/menu" replace />;
  }

  if (session) {
    return (
      <PlayPage
        sessionId={session.sessionId}
        storyName={session.storyName}
        initialTurns={session.initialTurns}
        getToken={getToken}
        onExit={(checkpointFailureMessage) => {
          // PlayPage unmounts as soon as this runs, so a failed exit-save's notice
          // (FR-006a) has to be shown here, once we're back on this screen.
          setCheckpointExitNotice(checkpointFailureMessage || null);
          setSession(null);
        }}
      />
    );
  }

  if (resumeSessionId) {
    if (resuming) {
      return (
        <PageContainer>
          <p className="text-muted">Resuming your story…</p>
        </PageContainer>
      );
    }
    // Reached either because resuming failed (resumeError set) or because the player
    // exited a successfully resumed session back to here (checkpointExitNotice, or
    // neither — a plain way back).
    return (
      <PageContainer>
        {resumeError && (
          <p role="alert" style={{ fontSize: "12px", color: "var(--color-accent-700)" }}>
            {resumeError}
          </p>
        )}
        {checkpointExitNotice && (
          <p role="status" className="text-muted" style={{ fontSize: "13px" }}>
            {checkpointExitNotice}
          </p>
        )}
        <Link to="/menu" className="btn btn-secondary">
          Back to Home
        </Link>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <h1 style={{ margin: 0, fontSize: "36px" }}>{adventureName || "Set up your game"}</h1>
      <hr className="hr" style={{ margin: "22px 0 32px" }} />
      {checkpointExitNotice && (
        <p role="status" className="text-muted" style={{ fontSize: "13px", margin: "8px 0 32px" }}>
          {checkpointExitNotice}
        </p>
      )}

      <section aria-labelledby="step1-heading">
        <h2 id="step1-heading" style={{ fontSize: "16px", margin: "0 0 12px" }}>
          01 — Name your character
        </h2>
        <CharacterNameStep value={characterName} onChange={setCharacterName} error={fieldErrors.characterName} />
      </section>

      <section aria-labelledby="step2-heading" style={{ marginTop: "40px" }}>
        <h2 id="step2-heading" style={{ fontSize: "16px", margin: "0 0 12px" }}>
          02 — Choose a character type
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
    </PageContainer>
  );
}

export default GamePage;
