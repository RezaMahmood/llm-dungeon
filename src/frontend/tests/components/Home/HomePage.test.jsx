import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

const acquireTokenSilent = vi.fn();
const listAdventures = vi.fn();
const listSavedGames = vi.fn();
const mockUseCapabilities = vi.fn();

const mockAccounts = [{ homeAccountId: "home-1", username: "ada@example.com", name: "Ada B." }];
const mockInstance = { acquireTokenSilent, logoutRedirect: vi.fn() };

vi.mock("@azure/msal-react", () => ({
  useMsal: () => ({ instance: mockInstance, accounts: mockAccounts }),
}));

vi.mock("../../../src/hooks/useCapabilities.js", () => ({
  useCapabilities: () => mockUseCapabilities(),
}));

vi.mock("../../../src/services/gameService.js", () => ({
  listAdventures: (...args) => listAdventures(...args),
  listSavedGames: (...args) => listSavedGames(...args),
}));

import HomePage from "../../../src/pages/HomePage.jsx";

function story(overrides = {}) {
  return {
    id: "story-1",
    name: "Nine Doors of Mudlark Hall",
    tone: "Mystery",
    sessionLengthMinutes: 20,
    readingLevel: "Year 5",
    blurb: "Every door tells you a rule. Eight of them are lying.",
    ...overrides,
  };
}

function session(overrides = {}) {
  return {
    sessionId: "session-1",
    adventureId: "story-2",
    adventureName: "The Lighthouse at Gullwing Cove",
    characterName: "Ada",
    locationLabel: "The keeper's stairs",
    progress: { current: 3, total: 5 },
    turnCount: 6,
    startedAt: "2026-09-01T00:00:00Z",
    lastInteractionAt: "2026-09-10T00:00:00Z",
    isActiveForPlayer: true,
    checkpointCount: 1,
    available: true,
    ...overrides,
  };
}

function grantedCapabilities(overrides = {}) {
  return {
    hasPlayer: true,
    hasAdministrator: false,
    loading: false,
    error: null,
    denied: false,
    refetch: vi.fn(),
    ...overrides,
  };
}

async function renderHome() {
  render(
    <MemoryRouter>
      <HomePage />
    </MemoryRouter>,
  );
  // Every scenario below waits for the loading state to clear before asserting.
  await screen.findByText(/ready to play/i);
}

describe("HomePage", () => {
  beforeEach(() => {
    acquireTokenSilent.mockReset().mockResolvedValue({ accessToken: "tok" });
    listAdventures.mockReset();
    listSavedGames.mockReset();
    mockUseCapabilities.mockReset();
  });

  it("state 1: no sessions — zero-state lede and 'Nothing in progress' with no card", async () => {
    mockUseCapabilities.mockReturnValue(grantedCapabilities());
    listAdventures.mockResolvedValueOnce({ adventures: [story()] });
    listSavedGames.mockResolvedValueOnce({ sessions: [] });

    await renderHome();

    expect(screen.getByText(/nothing on the go right now/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /nothing in progress/i })).toBeInTheDocument();
    expect(screen.getByText(/when you open a story it lands here/i)).toBeInTheDocument();
    expect(screen.getByText("Nine Doors of Mudlark Hall")).toBeInTheDocument();
  });

  it("state 2: one session — singular lede, one card, and the story is excluded from Ready to play (FR-004)", async () => {
    mockUseCapabilities.mockReturnValue(grantedCapabilities());
    listAdventures.mockResolvedValueOnce({ adventures: [story({ id: "story-2", name: "The Lighthouse at Gullwing Cove" }), story()] });
    listSavedGames.mockResolvedValueOnce({ sessions: [session()] });

    await renderHome();

    expect(screen.getByText(/you have one story on the go/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /^in progress$/i })).toBeInTheDocument();
    expect(screen.getByText("The Lighthouse at Gullwing Cove")).toBeInTheDocument();
    // The story behind the in-progress session must not also appear as ready-to-play.
    const readyColumn = screen.getByText(/ready to play/i).closest("section");
    expect(within(readyColumn).queryByText("The Lighthouse at Gullwing Cove")).not.toBeInTheDocument();
    expect(within(readyColumn).getByText("Nine Doors of Mudlark Hall")).toBeInTheDocument();
  });

  it("shows an explanatory message, not a blank column, when every published story already has a session", async () => {
    mockUseCapabilities.mockReturnValue(grantedCapabilities());
    listAdventures.mockResolvedValueOnce({ adventures: [story()] });
    listSavedGames.mockResolvedValueOnce({ sessions: [session({ adventureId: "story-1" })] });

    await renderHome();

    const readyColumn = screen.getByText(/ready to play/i).closest("section");
    expect(within(readyColumn).getByText(/you.ve started every story/i)).toBeInTheDocument();
  });

  it("state 3/6: many sessions — plural lede and every card renders (overflow scrolls, not paginates)", async () => {
    mockUseCapabilities.mockReturnValue(grantedCapabilities());
    const sessions = Array.from({ length: 10 }, (_, i) =>
      session({ sessionId: `session-${i}`, adventureId: `story-${i}`, adventureName: `Story ${i}` }),
    );
    listAdventures.mockResolvedValueOnce({ adventures: [story()] });
    listSavedGames.mockResolvedValueOnce({ sessions });

    await renderHome();

    expect(screen.getByText(/you have 10 stories on the go/i)).toBeInTheDocument();
    sessions.forEach((s) => expect(screen.getByText(s.adventureName)).toBeInTheDocument());
  });

  it("FR-018: an unavailable session is visibly marked and its Resume is disabled", async () => {
    mockUseCapabilities.mockReturnValue(grantedCapabilities());
    listAdventures.mockResolvedValueOnce({ adventures: [] });
    listSavedGames.mockResolvedValueOnce({ sessions: [session({ available: false })] });

    await renderHome();

    // Both the status tag and the disabled Resume control read "Unavailable".
    expect(screen.getAllByText(/unavailable/i).length).toBeGreaterThanOrEqual(2);
    expect(screen.queryByRole("button", { name: /^resume$/i })).not.toBeInTheDocument();
  });

  it("FR-017: denied account sees the access-denied screen, not story columns", async () => {
    mockUseCapabilities.mockReturnValue(grantedCapabilities({ hasPlayer: false, denied: true }));

    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(/access not granted/i);
    expect(listAdventures).not.toHaveBeenCalled();
  });

  it("FR-017: an account with no capabilities sees Access Pending, not empty columns", async () => {
    mockUseCapabilities.mockReturnValue(grantedCapabilities({ hasPlayer: false, hasAdministrator: false }));

    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    );

    expect(await screen.findByText(/access pending/i)).toBeInTheDocument();
    expect(listAdventures).not.toHaveBeenCalled();
  });
});
