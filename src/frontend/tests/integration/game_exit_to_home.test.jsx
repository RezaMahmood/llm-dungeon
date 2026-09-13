/**
 * Confirming pause-and-exit takes the player to Home (#346), whether the exit checkpoint
 * saved or not (009-save-and-continue FR-006/FR-006a). Before this, exiting dropped the
 * player back onto GamePage's resume shell — a near-empty screen holding only a
 * "Back to Home" link — or onto its character-setup form.
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

const acquireTokenSilent = vi.fn();
const mockInstance = { acquireTokenSilent, logoutRedirect: vi.fn() };
const mockAccounts = [{ homeAccountId: "home-1", username: "player@example.com", name: "Ada B." }];

vi.mock("@azure/msal-react", () => ({
  useMsal: () => ({ instance: mockInstance, accounts: mockAccounts }),
}));

vi.mock("../../src/hooks/useCapabilities.js", () => ({
  useCapabilities: () => ({ hasPlayer: true, hasAdministrator: false, loading: false, error: null, denied: false, refetch: vi.fn() }),
}));

const listAdventures = vi.fn();
const listSavedGames = vi.fn();
const getAdventure = vi.fn();
const createSession = vi.fn();
const getSession = vi.fn();
const resumeSession = vi.fn();
const saveCheckpoint = vi.fn();

vi.mock("../../src/services/gameService.js", () => ({
  listAdventures: (...args) => listAdventures(...args),
  listSavedGames: (...args) => listSavedGames(...args),
  getAdventure: (...args) => getAdventure(...args),
  createSession: (...args) => createSession(...args),
  getSession: (...args) => getSession(...args),
  resumeSession: (...args) => resumeSession(...args),
  saveCheckpoint: (...args) => saveCheckpoint(...args),
  submitInteraction: vi.fn(),
  deleteSession: vi.fn(),
}));

import TitleBar from "../../src/components/Layout/TitleBar.jsx";
import { PlayTitleProvider } from "../../src/context/PlayTitleContext.jsx";
import GamePage from "../../src/pages/GamePage.jsx";
import HomePage from "../../src/pages/HomePage.jsx";

const STORY = {
  id: "a1",
  name: "The Lighthouse at Gullwing Cove",
  tone: "Mystery",
  sessionLengthMinutes: 20,
  readingLevel: "Year 5",
  blurb: "A keeper who never left.",
  characterTypes: [{ name: "Scout", description: "Quick and quiet." }],
};

const SESSION_DETAIL = {
  sessionId: "session-1",
  adventureId: "a1",
  adventureName: STORY.name,
  characterName: "Bramble",
  characterType: "Scout",
  status: "active",
  completionReason: null,
  isActiveForPlayer: true,
  locationLabel: "The keeper's stairs",
  progress: { current: 3, total: 5 },
  turnCount: 2,
  checkpointCount: 0,
  startedAt: "2026-09-01T18:22:04Z",
  lastInteractionAt: "2026-09-05T20:11:47Z",
  turns: [
    { turnNumber: 0, playerInput: null, narrativeText: "The door creaks open.", suggestedActions: ["look"], locationLabel: "Entrance", goalLabel: null, progress: null, timestamp: "t0" },
    { turnNumber: 1, playerInput: "look", narrativeText: "You find the stairs.", suggestedActions: ["climb"], locationLabel: "The keeper's stairs", goalLabel: null, progress: { current: 3, total: 5 }, timestamp: "t1" },
  ],
  checkpoints: [],
};

/** Both routes wired as the app wires them, so an exit's navigation really lands. */
function renderApp(initialEntries) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <PlayTitleProvider>
        <TitleBar />
        <Routes>
          <Route path="/game" element={<GamePage />} />
          <Route path="/menu" element={<HomePage />} />
        </Routes>
      </PlayTitleProvider>
    </MemoryRouter>,
  );
}

async function confirmPauseAndExit(user) {
  await user.click(screen.getByRole("button", { name: /pause & exit/i }));
  await user.click(screen.getByRole("button", { name: /save and exit to my stories/i }));
}

describe("Pause and exit lands the player on Home (#346)", () => {
  beforeEach(() => {
    acquireTokenSilent.mockReset().mockResolvedValue({ accessToken: "tok" });
    listAdventures.mockReset().mockResolvedValue({ adventures: [STORY] });
    listSavedGames.mockReset().mockResolvedValue({ sessions: [] });
    getAdventure.mockReset().mockResolvedValue({ adventure: STORY });
    createSession.mockReset();
    getSession.mockReset().mockResolvedValue({ status: "success", session: SESSION_DETAIL });
    resumeSession.mockReset().mockResolvedValue({ status: "active", sessionId: "session-1" });
    saveCheckpoint.mockReset();
  });

  it("goes to Home when the exit checkpoint saves, with no failure notice", async () => {
    saveCheckpoint.mockResolvedValue({ checkpoint: { label: "The keeper's stairs", turnNumber: 1, createdAt: "now" } });
    const user = userEvent.setup();
    renderApp([{ pathname: "/game", state: { resumeSessionId: "session-1", isActiveForPlayer: false } }]);

    await screen.findByText("You find the stairs.");
    await confirmPauseAndExit(user);

    // Home, not GamePage's resume shell.
    expect(await screen.findByText(/ready to play/i)).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /back to home/i })).not.toBeInTheDocument();
    expect(screen.queryByText(/couldn't record that checkpoint/i)).not.toBeInTheDocument();
  });

  it("still goes to Home when the exit checkpoint fails, carrying the notice there (FR-006a)", async () => {
    saveCheckpoint.mockRejectedValue(new Error("network error"));
    const user = userEvent.setup();
    renderApp([{ pathname: "/game", state: { resumeSessionId: "session-1", isActiveForPlayer: false } }]);

    await screen.findByText("You find the stairs.");
    await confirmPauseAndExit(user);

    expect(await screen.findByText(/couldn't record that checkpoint/i)).toBeInTheDocument();
    expect(screen.getByText(/ready to play/i)).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /back to home/i })).not.toBeInTheDocument();
  });

  it("goes to Home from a freshly created session too, not back to the setup form", async () => {
    createSession.mockResolvedValue({
      sessionId: "session-2",
      narrative: { turnNumber: 0, playerInput: null, narrativeText: "The door creaks open.", suggestedActions: ["look"], locationLabel: "Entrance", goalLabel: null, progress: null, timestamp: "t0" },
    });
    saveCheckpoint.mockResolvedValue({ checkpoint: { label: "Entrance", turnNumber: 0, createdAt: "now" } });
    const user = userEvent.setup();
    renderApp([{ pathname: "/game", state: { adventureId: "a1" } }]);

    await user.type(await screen.findByLabelText(/character name/i), "Bramble");
    await user.click(await screen.findByText("Scout"));
    await user.click(screen.getByRole("button", { name: /start playing/i }));

    await screen.findByText("The door creaks open.");
    await confirmPauseAndExit(user);

    expect(await screen.findByText(/ready to play/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /start playing/i })).not.toBeInTheDocument();
  });
});
