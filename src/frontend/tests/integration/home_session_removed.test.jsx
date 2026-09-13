import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

const acquireTokenSilent = vi.fn().mockResolvedValue({ accessToken: "tok" });
const mockAccounts = [{ homeAccountId: "home-1", username: "ada@example.test", name: "Ada B." }];
const mockInstance = { acquireTokenSilent, logoutRedirect: vi.fn() };

vi.mock("@azure/msal-react", () => ({
  useMsal: () => ({ instance: mockInstance, accounts: mockAccounts }),
}));

vi.mock("../../src/hooks/useCapabilities.js", () => ({
  useCapabilities: () => ({
    hasPlayer: true,
    hasAdministrator: false,
    loading: false,
    error: null,
    denied: false,
    refetch: vi.fn(),
  }),
}));

const listAdventures = vi.fn();
const listSavedGames = vi.fn();
const getSession = vi.fn();
const resumeSession = vi.fn();
const getAdventure = vi.fn();

vi.mock("../../src/services/gameService.js", () => ({
  listAdventures: (...args) => listAdventures(...args),
  listSavedGames: (...args) => listSavedGames(...args),
  getSession: (...args) => getSession(...args),
  resumeSession: (...args) => resumeSession(...args),
  getAdventure: (...args) => getAdventure(...args),
  createSession: vi.fn(),
  saveCheckpoint: vi.fn(),
  submitInteraction: vi.fn(),
  deleteSession: vi.fn(),
}));

import GamePage from "../../src/pages/GamePage.jsx";
import HomePage from "../../src/pages/HomePage.jsx";

const SESSION_REMOVED = {
  response: {
    status: 404,
    data: {
      error: "session_removed",
      message: "This session has been removed. You can start this story again from your home page.",
      promptReturnToList: true,
    },
  },
};

const STORY = {
  id: "story-2",
  name: "The Lighthouse at Gullwing Cove",
  tone: "Mystery",
  sessionLengthMinutes: 20,
  readingLevel: "Year 5",
  blurb: "A keeper who never left.",
};

// Enters at /game the way Home's Resume does — route state carrying the session id.
function renderResumeInto(initialEntries) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <Routes>
        <Route path="/game" element={<GamePage />} />
        <Route path="/menu" element={<HomePage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("A player whose session was deleted underneath them (031 FR-011/FR-012/FR-013)", () => {
  beforeEach(() => {
    listAdventures.mockReset().mockResolvedValue({ adventures: [STORY] });
    // The session is gone, so the server no longer lists it (FR-011).
    listSavedGames.mockReset().mockResolvedValue({ sessions: [] });
    getSession.mockReset();
    resumeSession.mockReset().mockResolvedValue({});
    getAdventure.mockReset().mockResolvedValue({ adventure: { ...STORY, characterTypes: [] } });
  });

  it("lands on Home with a dialog explaining the session is gone", async () => {
    getSession.mockRejectedValue(SESSION_REMOVED);

    renderResumeInto([{ pathname: "/game", state: { resumeSessionId: "session-1", isActiveForPlayer: true } }]);

    const dialog = await screen.findByRole("dialog");
    expect(dialog).toHaveTextContent(/this session has been removed/i);
    // Names no actor (research.md Decision 4).
    expect(dialog).not.toHaveTextContent(/administrator/i);
  });

  it("leaves a working, current Home once the dialog is dismissed", async () => {
    getSession.mockRejectedValue(SESSION_REMOVED);
    const user = userEvent.setup();

    renderResumeInto([{ pathname: "/game", state: { resumeSessionId: "session-1", isActiveForPlayer: true } }]);

    await screen.findByRole("dialog");
    await user.click(screen.getByRole("button", { name: /got it/i }));

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    // FR-013: the story is there to start again, and FR-011: the session is not listed.
    expect(await screen.findByText(STORY.name)).toBeInTheDocument();
    expect(screen.queryByText(/the keeper's stairs/i)).not.toBeInTheDocument();
  });

  it("does not tell the player their story was deleted — the story is still alive", async () => {
    getSession.mockRejectedValue(SESSION_REMOVED);

    renderResumeInto([{ pathname: "/game", state: { resumeSessionId: "session-1", isActiveForPlayer: true } }]);

    await screen.findByRole("dialog");
    expect(screen.queryByText(/story has been deleted/i)).not.toBeInTheDocument();
  });

  it("shows nothing at all to a player who simply opens Home after the deletion", async () => {
    render(
      <MemoryRouter initialEntries={["/menu"]}>
        <Routes>
          <Route path="/menu" element={<HomePage />} />
        </Routes>
      </MemoryRouter>,
    );

    // FR-011: absent from the list, with no dialog, placeholder, or error.
    expect(await screen.findByText(STORY.name)).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
