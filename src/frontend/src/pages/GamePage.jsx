/**
 * 3-step adventure/character setup flow (006-adventure-and-character-setup): pick a
 * published adventure, name a character, choose a character type — in that order
 * (FR-003a) — then confirm to start play. Replaces the prior placeholder; the header for
 * this screen is the compact TitleBar supplied by AuthenticatedLayout (FR-006 of
 * 019-spa-refresh-button).
 *
 * Full gameplay itself lands in 008-core-gameplay; this page only validates and confirms
 * setup (POST /api/game/start does not create a play session yet).
 */
import { useMsal } from "@azure/msal-react";
import { useCallback, useEffect, useRef, useState } from "react";

import AdventureList from "../components/GameSetup/AdventureList.jsx";
import CharacterNameStep, { MAX_CHARACTER_NAME_LENGTH } from "../components/GameSetup/CharacterNameStep.jsx";
import CharacterTypeStep from "../components/GameSetup/CharacterTypeStep.jsx";
import { getAdventure, listAdventures, startGame } from "../services/gameService.js";
import { loginRequest } from "../services/msalConfig.js";

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
  const accountKey = account?.homeAccountId || account?.username || "";

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
  const [started, setStarted] = useState(null);
  const accountRef = useRef(account);
  const isMountedRef = useRef(true);
  const adventureRequestIdRef = useRef(0);

  useEffect(() => {
    accountRef.current = account;
  }, [account]);

  useEffect(
    () => () => {
      isMountedRef.current = false;
    },
    [],
  );

  const getToken = useCallback(async () => {
    const tokenResponse = await instance.acquireTokenSilent({ ...loginRequest, account: accountRef.current });
    return tokenResponse.accessToken;
  }, [instance, accountKey]);

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
      setStarted(null);

      const requestId = ++adventureRequestIdRef.current;
      setTypesLoading(true);
      setTypesError(null);
      (async () => {
        try {
          const token = await getToken();
          const data = await getAdventure(token, id);
          if (isMountedRef.current && requestId === adventureRequestIdRef.current) {
            setCharacterTypes(data.adventure?.characterTypes || []);
          }
        } catch (err) {
          if (isMountedRef.current && requestId === adventureRequestIdRef.current) {
            setTypesError(err);
          }
        } finally {
          if (isMountedRef.current && requestId === adventureRequestIdRef.current) {
            setTypesLoading(false);
          }
        }
      })();
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
      const data = await startGame(token, { adventureId, characterName: characterName.trim(), characterType });
      setStarted(data);
    } catch (err) {
      setFieldErrors(err.response?.data?.fields || { adventureId: "Something went wrong. Please try again." });
    } finally {
      setSubmitting(false);
    }
  };

  const step1Done = Boolean(adventureId);

  return (
    <div style={{ maxWidth: "1020px", padding: "var(--space-6) var(--space-4) 64px" }}>
      <h1 style={{ margin: 0, fontSize: "36px" }}>Set up your game</h1>
      <hr className="hr" style={{ margin: "22px 0 32px" }} />

      <section aria-labelledby="step1-heading">
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
        {started && (
          <p className="text-muted" style={{ margin: 0 }}>
            Setup complete — playing as {started.characterName} ({started.characterType}).
          </p>
        )}
      </div>
    </div>
  );
}

export default GamePage;
