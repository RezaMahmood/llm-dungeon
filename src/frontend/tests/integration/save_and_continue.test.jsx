import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const acquireTokenSilent = vi.fn();
const listAdventures = vi.fn();
const getAdventure = vi.fn();
const createSession = vi.fn();
const listSavedGames = vi.fn();
const getSession = vi.fn();
const resumeSession = vi.fn();
const submitInteraction = vi.fn();
const saveCheckpoint = vi.fn();

const mockInstance = { acquireTokenSilent };
const mockAccounts = [{ homeAccountId: "home-1", username: "player@example.com" }];

vi.mock("@azure/msal-react", () => ({
  useMsal: () => ({ instance: mockInstance, accounts: mockAccounts }),
}));

vi.mock("../../src/services/gameService.js", () => ({
  listAdventures: (...args) => listAdventures(...args),
  getAdventure: (...args) => getAdventure(...args),
  createSession: (...args) => createSession(...args),
  listSavedGames: (...args) => listSavedGames(...args),
  getSession: (...args) => getSession(...args),
  resumeSession: (...args) => resumeSession(...args),
  submitInteraction: (...args) => submitInteraction(...args),
  saveCheckpoint: (...args) => saveCheckpoint(...args),
}));

import GamePage from "../../src/pages/GamePage.jsx";

const SAVED_GAME = {
  sessionId: "session-1",
  adventureId: "a1",
  adventureName: "The Lighthouse at Gullwing Cove",
  characterName: "Bramble",
  locationLabel: "The keeper's stairs",
  progress: { current: 3, total: 5 },
  turnCount: 2,
  startedAt: "2026-09-01T18:22:04Z",
  lastInteractionAt: "2026-09-05T20:11:47Z",
  isActiveForPlayer: false,
  checkpointCount: 0,
};

const SESSION_DETAIL = {
  sessionId: "session-1",
  adventureId: "a1",
  adventureName: "The Lighthouse at Gullwing Cove",
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

describe("Save and continue: list -> Resume -> play (009-save-and-continue)", () => {
  beforeEach(() => {
    acquireTokenSilent.mockReset().mockResolvedValue({ accessToken: "tok" });
    listAdventures.mockReset().mockResolvedValue({ adventures: [] });
    getAdventure.mockReset();
    createSession.mockReset();
    listSavedGames.mockReset().mockResolvedValue({ sessions: [SAVED_GAME] });
    getSession.mockReset().mockResolvedValue({ status: "success", session: SESSION_DETAIL });
    resumeSession.mockReset();
  });

  it("calls resume before fetching the session when the row isn't already active", async () => {
    resumeSession.mockResolvedValue({ status: "active", sessionId: "session-1" });
    const user = userEvent.setup();
    render(<GamePage />);

    await user.click(await screen.findByRole("button", { name: /resume/i }));

    expect(await screen.findByText("You find the stairs.")).toBeInTheDocument();
    expect(resumeSession).toHaveBeenCalledWith("tok", "session-1");
    expect(getSession).toHaveBeenCalledWith("tok", "session-1");
    // Every prior turn renders, oldest first.
    expect(screen.getByText("The door creaks open.")).toBeInTheDocument();
  });

  it("never calls resume when the row is already the player's active game", async () => {
    listSavedGames.mockResolvedValue({ sessions: [{ ...SAVED_GAME, isActiveForPlayer: true }] });
    const user = userEvent.setup();
    render(<GamePage />);

    await user.click(await screen.findByRole("button", { name: /resume/i }));

    expect(await screen.findByText("You find the stairs.")).toBeInTheDocument();
    expect(resumeSession).not.toHaveBeenCalled();
  });

  it("treats a stale row's 409 already_active as success, with no error shown", async () => {
    resumeSession.mockRejectedValue({ response: { status: 409, data: { error: "already_active" } } });
    const user = userEvent.setup();
    render(<GamePage />);

    await user.click(await screen.findByRole("button", { name: /resume/i }));

    expect(await screen.findByText("You find the stairs.")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("shows an error and stays on the stories screen when resume genuinely fails", async () => {
    resumeSession.mockRejectedValue({ response: { status: 409, data: { error: "session_concluded" } } });
    const user = userEvent.setup();
    render(<GamePage />);

    await user.click(await screen.findByRole("button", { name: /resume/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/couldn't resume this story/i);
    expect(getSession).not.toHaveBeenCalled();
  });
});
