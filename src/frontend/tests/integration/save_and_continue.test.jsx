import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

const acquireTokenSilent = vi.fn();
const logoutRedirect = vi.fn();
const listAdventures = vi.fn();
const getAdventure = vi.fn();
const createSession = vi.fn();
const listSavedGames = vi.fn();
const getSession = vi.fn();
const resumeSession = vi.fn();
const submitInteraction = vi.fn();
const saveCheckpoint = vi.fn();

const mockInstance = { acquireTokenSilent, logoutRedirect };
const mockAccounts = [{ homeAccountId: "home-1", username: "player@example.com" }];

vi.mock("@azure/msal-react", () => ({
  useMsal: () => ({ instance: mockInstance, accounts: mockAccounts }),
}));

vi.mock("../../src/hooks/useCapabilities.js", () => ({
  useCapabilities: () => ({ hasPlayer: true, hasAdministrator: false, loading: false, error: null, denied: false, refetch: vi.fn() }),
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

import NavBar from "../../src/components/Layout/NavBar.jsx";
import TitleBar from "../../src/components/Layout/TitleBar.jsx";
import { PlayTitleProvider } from "../../src/context/PlayTitleContext.jsx";
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

  it("shows a checkpoint-failure notice back on the stories screen after Save and exit fails", async () => {
    resumeSession.mockResolvedValue({ status: "active", sessionId: "session-1" });
    saveCheckpoint.mockRejectedValue(new Error("network error"));
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <PlayTitleProvider>
          <TitleBar />
          <GamePage />
        </PlayTitleProvider>
      </MemoryRouter>,
    );

    await user.click(await screen.findByRole("button", { name: /resume/i }));
    await screen.findByText("You find the stairs.");

    await user.click(screen.getByRole("button", { name: /pause & exit/i }));
    await user.click(screen.getByRole("button", { name: /save and exit to my stories/i }));

    expect(await screen.findByText(/couldn't record that checkpoint/i)).toBeInTheDocument();
    // Back on the stories screen, not stuck on the play surface.
    expect(await screen.findByRole("heading", { name: /choose an adventure/i })).toBeInTheDocument();
  });
});

describe("Save and continue: sign-out round trip (009-save-and-continue, US2 Acceptance Scenarios 3-4)", () => {
  beforeEach(() => {
    acquireTokenSilent.mockReset().mockResolvedValue({ accessToken: "tok" });
    logoutRedirect.mockReset();
    listAdventures.mockReset().mockResolvedValue({ adventures: [] });
    getAdventure.mockReset();
    createSession.mockReset();
    listSavedGames.mockReset();
    getSession.mockReset();
    resumeSession.mockReset();
    saveCheckpoint.mockReset();
  });

  it("accepting the prompt records a marker and the resumed game later shows every turn plus the marker", async () => {
    listSavedGames.mockResolvedValue({
      sessions: [{ ...SAVED_GAME, status: "active", isActiveForPlayer: true }],
    });
    saveCheckpoint.mockResolvedValue({ checkpoint: { label: "The keeper's stairs", turnNumber: 1, createdAt: "now" } });
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <NavBar />
      </MemoryRouter>,
    );

    await user.click(screen.getByRole("link", { name: "Sign out" }));
    await screen.findByRole("dialog");
    await user.click(screen.getByRole("button", { name: /save and sign out/i }));

    expect(saveCheckpoint).toHaveBeenCalledWith("tok", "session-1");

    // Resuming afterwards shows every turn, plus the newly recorded marker.
    getSession.mockResolvedValue({
      status: "success",
      session: { ...SESSION_DETAIL, checkpoints: [{ label: "The keeper's stairs", turnNumber: 1, createdAt: "now" }] },
    });
    render(<GamePage />);
    await user.click(await screen.findByRole("button", { name: /resume/i }));

    expect(await screen.findByText("You find the stairs.")).toBeInTheDocument();
    expect(screen.getByText("The door creaks open.")).toBeInTheDocument();
  });

  it("declining records none and the resumed game shows exactly the same turns", async () => {
    listSavedGames.mockResolvedValue({
      sessions: [{ ...SAVED_GAME, status: "active", isActiveForPlayer: true }],
    });
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <NavBar />
      </MemoryRouter>,
    );

    await user.click(screen.getByRole("link", { name: "Sign out" }));
    await screen.findByRole("dialog");
    await user.click(screen.getByRole("button", { name: /sign out without saving/i }));

    expect(saveCheckpoint).not.toHaveBeenCalled();

    getSession.mockResolvedValue({ status: "success", session: SESSION_DETAIL });
    render(<GamePage />);
    await user.click(await screen.findByRole("button", { name: /resume/i }));

    expect(await screen.findByText("You find the stairs.")).toBeInTheDocument();
    expect(screen.getByText("The door creaks open.")).toBeInTheDocument();
  });
});

// Resuming is the *first* thing a player does after leaving a game, so it — not
// submitting a turn — is where they normally first meet a story that became
// unavailable while the row sat on their screen. Both calls `handleResume` makes can
// report it, and each reason gets its own specific message rather than the shared
// generic one (025-story-delete-done FR-007, FR-008, contracts/api.md Validation Rules).
describe("Resuming a story that became unavailable (025-story-delete-done FR-007, FR-008)", () => {
  const DELETED = {
    response: {
      status: 404,
      data: {
        error: "story_deleted",
        message: "Story has been deleted. You can no longer continue this story.",
        promptReturnToList: true,
      },
    },
  };
  const UNPUBLISHED = {
    response: {
      status: 409,
      data: {
        error: "story_unpublished",
        message: "Story has been unpublished. You can no longer continue this story.",
        promptReturnToList: true,
      },
    },
  };

  beforeEach(() => {
    acquireTokenSilent.mockReset().mockResolvedValue({ accessToken: "tok" });
    listAdventures.mockReset().mockResolvedValue({ adventures: [] });
    getAdventure.mockReset();
    createSession.mockReset();
    listSavedGames.mockReset().mockResolvedValue({ sessions: [SAVED_GAME] });
    getSession.mockReset().mockResolvedValue({ status: "success", session: SESSION_DETAIL });
    resumeSession.mockReset();
    saveCheckpoint.mockReset();
  });

  it("shows the specific deleted notice and drops the row when resume reports story_deleted", async () => {
    resumeSession.mockRejectedValue(DELETED);
    const user = userEvent.setup();
    render(<GamePage />);

    await user.click(await screen.findByRole("button", { name: /resume/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/story has been deleted/i);
    expect(screen.getByRole("alert")).not.toHaveTextContent(/couldn't resume this story/i);
    // The session was permanently removed along with its story (FR-004, FR-010), so
    // the row goes with it rather than offering a Resume that can only fail again.
    expect(screen.queryByRole("button", { name: /^resume$/i })).not.toBeInTheDocument();
    // The row's title span renders the adventure and character together, so match on
    // a substring rather than the bare adventure name.
    expect(screen.queryByText(/Gullwing Cove/)).not.toBeInTheDocument();
    // Never hands off to the play surface.
    expect(getSession).not.toHaveBeenCalled();
  });

  it("shows the specific unpublished notice and greys the row when resume reports story_unpublished", async () => {
    resumeSession.mockRejectedValue(UNPUBLISHED);
    const user = userEvent.setup();
    render(<GamePage />);

    await user.click(await screen.findByRole("button", { name: /resume/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/story has been unpublished/i);
    expect(screen.getByRole("alert")).not.toHaveTextContent(/couldn't resume this story/i);
    // Unpublish never deletes the session (FR-005) — the row stays, marked
    // non-continuable exactly as the next list load would render it (FR-009).
    expect(screen.getByText(/Gullwing Cove/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /unavailable/i })).toBeDisabled();
    expect(getSession).not.toHaveBeenCalled();
  });

  it("reports story_deleted the same way when it comes from the session fetch rather than resume", async () => {
    // `handleResume` calls resume and getSession inside one try — a story deleted
    // between the two must not fall through to the generic message either.
    resumeSession.mockResolvedValue({ status: "active", sessionId: "session-1" });
    getSession.mockRejectedValue(DELETED);
    const user = userEvent.setup();
    render(<GamePage />);

    await user.click(await screen.findByRole("button", { name: /resume/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/story has been deleted/i);
    expect(screen.queryByRole("button", { name: /^resume$/i })).not.toBeInTheDocument();
  });

  it("reports story_unpublished the same way when it comes from the session fetch rather than resume", async () => {
    resumeSession.mockResolvedValue({ status: "active", sessionId: "session-1" });
    getSession.mockRejectedValue(UNPUBLISHED);
    const user = userEvent.setup();
    render(<GamePage />);

    await user.click(await screen.findByRole("button", { name: /resume/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/story has been unpublished/i);
    expect(screen.getByRole("button", { name: /unavailable/i })).toBeDisabled();
  });

  it("still shows the generic message for a failure that is neither", async () => {
    resumeSession.mockRejectedValue({ response: { status: 409, data: { error: "session_concluded" } } });
    const user = userEvent.setup();
    render(<GamePage />);

    await user.click(await screen.findByRole("button", { name: /resume/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/couldn't resume this story/i);
    // The row is untouched — only the two story-unavailable reasons change it.
    expect(screen.getByRole("button", { name: /^resume$/i })).toBeInTheDocument();
  });
});
