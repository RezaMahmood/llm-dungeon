import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

const acquireTokenSilent = vi.fn().mockResolvedValue({ accessToken: "tok" });
const mockInstance = { acquireTokenSilent, logoutRedirect: vi.fn() };
const mockAccounts = [{ homeAccountId: "home-1", username: "ada@example.test", name: "Ada B." }];

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

vi.mock("../../src/services/gameService.js", () => ({
  listAdventures: (...args) => listAdventures(...args),
  listSavedGames: (...args) => listSavedGames(...args),
  getAdventure: (...args) => getAdventure(...args),
  createSession: (...args) => createSession(...args),
  getSession: (...args) => getSession(...args),
  resumeSession: (...args) => resumeSession(...args),
  submitInteraction: vi.fn(),
}));

import HomePage from "../../src/pages/HomePage.jsx";
import GamePage from "../../src/pages/GamePage.jsx";

const STORY = {
  id: "story-1",
  name: "Nine Doors of Mudlark Hall",
  tone: "Mystery",
  sessionLengthMinutes: 20,
  readingLevel: "Year 5",
  blurb: "Every door tells you a rule. Eight of them are lying.",
};

const IN_PROGRESS_SESSION = {
  sessionId: "session-1",
  adventureId: "story-2",
  adventureName: "The Lighthouse at Gullwing Cove",
  characterName: "Bramble",
  locationLabel: "The keeper's stairs",
  progress: { current: 3, total: 5 },
  turnCount: 2,
  startedAt: "2026-09-01T00:00:00Z",
  lastInteractionAt: "2026-09-05T00:00:00Z",
  isActiveForPlayer: false,
  checkpointCount: 0,
  available: true,
};

/** The two real routes involved, exactly as App.jsx wires them, so Home's navigate()
 * calls land on an actual GamePage rather than a stand-in. */
function renderApp(initialPath = "/menu") {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/menu" element={<HomePage />} />
        <Route path="/game" element={<GamePage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("Home -> Play -> character setup -> session start (FR-006, SC-002)", () => {
  beforeEach(() => {
    listAdventures.mockReset().mockResolvedValue({ adventures: [STORY] });
    listSavedGames.mockReset().mockResolvedValue({ sessions: [] });
    getAdventure.mockReset().mockResolvedValue({
      adventure: { id: "story-1", name: STORY.name, characterTypes: [{ name: "Detective", description: "Sharp-eyed." }] },
    });
    createSession.mockReset();
  });

  it("enters character setup directly with no adventure-picker step, then starts a session", async () => {
    const user = userEvent.setup();
    renderApp("/menu");

    await user.click(await screen.findByRole("link", { name: /play/i }));

    // Character-name entry appears immediately — no re-pick of the story Home already
    // showed (research.md Decision 4).
    expect(await screen.findByLabelText(/character name/i)).toBeInTheDocument();
    expect(screen.getByText(STORY.name)).toBeInTheDocument();
    expect(getAdventure).toHaveBeenCalledWith("tok", "story-1");

    createSession.mockResolvedValue({
      status: "success",
      sessionId: "session-new",
      narrative: { turnNumber: 0, narrativeText: "A door creaks open.", suggestedActions: ["look"], locationLabel: "Hall", goalLabel: null, progress: null },
    });
    await user.type(screen.getByLabelText(/character name/i), "Wren");
    await user.click(await screen.findByRole("radio", { name: /detective/i }));
    await user.click(screen.getByRole("button", { name: /start playing/i }));

    expect(await screen.findByText(/a door creaks open/i)).toBeInTheDocument();
    expect(createSession).toHaveBeenCalledWith("tok", { adventureId: "story-1", characterName: "Wren", characterType: "Detective" });
  });
});

describe("Home -> Resume -> session reopened without character setup (FR-007, SC-002)", () => {
  beforeEach(() => {
    listAdventures.mockReset().mockResolvedValue({ adventures: [] });
    listSavedGames.mockReset().mockResolvedValue({ sessions: [IN_PROGRESS_SESSION] });
    resumeSession.mockReset().mockResolvedValue({ status: "active", sessionId: "session-1" });
    getSession.mockReset().mockResolvedValue({
      status: "success",
      session: {
        sessionId: "session-1",
        adventureName: IN_PROGRESS_SESSION.adventureName,
        turns: [{ turnNumber: 2, narrativeText: "You reach the top of the stairs.", suggestedActions: ["Look around"], locationLabel: "The keeper's stairs", goalLabel: null, progress: { current: 3, total: 5 } }],
      },
    });
  });

  it("reopens the exact session, skipping character setup entirely", async () => {
    const user = userEvent.setup();
    renderApp("/menu");

    await user.click(await screen.findByRole("link", { name: /resume/i }));

    expect(await screen.findByText(/you reach the top of the stairs/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/character name/i)).not.toBeInTheDocument();
    expect(resumeSession).toHaveBeenCalledWith("tok", "session-1");
    expect(getSession).toHaveBeenCalledWith("tok", "session-1");
  });
});
