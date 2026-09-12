import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

const acquireTokenSilent = vi.fn().mockResolvedValue({ accessToken: "tok" });
const mockAccounts = [{ homeAccountId: "home-1", username: "ada@example.test", name: "Ada B." }];

vi.mock("@azure/msal-react", () => ({
  useMsal: () => ({ instance: { acquireTokenSilent, logoutRedirect: vi.fn() }, accounts: mockAccounts }),
}));

vi.mock("../../src/hooks/useCapabilities.js", () => ({
  useCapabilities: () => ({ hasPlayer: true, hasAdministrator: false, loading: false, error: null, denied: false, refetch: vi.fn() }),
}));

const listAdventures = vi.fn();
const listSavedGames = vi.fn();
const deleteSession = vi.fn();

vi.mock("../../src/services/gameService.js", () => ({
  listAdventures: (...args) => listAdventures(...args),
  listSavedGames: (...args) => listSavedGames(...args),
  deleteSession: (...args) => deleteSession(...args),
}));

import HomePage from "../../src/pages/HomePage.jsx";

const STORY = {
  id: "story-2",
  name: "The Lighthouse at Gullwing Cove",
  tone: "Mystery",
  sessionLengthMinutes: 20,
  readingLevel: "Year 5",
  blurb: "A keeper who never left.",
};

function inProgressSession(overrides = {}) {
  return {
    sessionId: "session-1",
    adventureId: "story-2",
    adventureName: "The Lighthouse at Gullwing Cove",
    locationLabel: "The keeper's stairs",
    progress: { current: 3, total: 5 },
    lastInteractionAt: "2026-09-10T00:00:00Z",
    isActiveForPlayer: false,
    available: true,
    ...overrides,
  };
}

async function renderHome() {
  render(
    <MemoryRouter>
      <HomePage />
    </MemoryRouter>,
  );
  await screen.findByRole("heading", { name: /ready to play/i });
}

describe("Home delete-session flow (User Story 3, FR-008/FR-009)", () => {
  beforeEach(() => {
    listAdventures.mockReset();
    listSavedGames.mockReset();
    deleteSession.mockReset();
  });

  it("confirm removes the card and the story reappears in Ready to play, with no refetch", async () => {
    listAdventures.mockResolvedValueOnce({ adventures: [STORY] });
    listSavedGames.mockResolvedValueOnce({ sessions: [inProgressSession()] });
    deleteSession.mockResolvedValue({ status: "deleted", sessionId: "session-1" });
    const user = userEvent.setup();
    await renderHome();

    expect(screen.getByText(STORY.name)).toBeInTheDocument();
    const readySection = screen.getByRole("heading", { name: /ready to play/i }).closest("section");
    expect(within(readySection).queryByText(STORY.name)).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /delete this session/i }));
    await user.click(await screen.findByRole("button", { name: /^delete$/i }));

    // The card is gone and the story now appears in Ready to play.
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /nothing in progress/i })).toBeInTheDocument();
    expect(within(readySection).getByText(STORY.name)).toBeInTheDocument();
    // FR-009: no refetch — one initial load of each list only.
    expect(listAdventures).toHaveBeenCalledTimes(1);
    expect(listSavedGames).toHaveBeenCalledTimes(1);
  });

  it("cancel leaves the card and the lede count in place", async () => {
    listAdventures.mockResolvedValueOnce({ adventures: [] });
    listSavedGames.mockResolvedValueOnce({ sessions: [inProgressSession()] });
    const user = userEvent.setup();
    await renderHome();

    expect(screen.getByText(/you have one story on the go/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /delete this session/i }));
    await user.click(await screen.findByRole("button", { name: /^cancel$/i }));

    expect(screen.getByText(STORY.name)).toBeInTheDocument();
    expect(screen.getByText(/you have one story on the go/i)).toBeInTheDocument();
    expect(deleteSession).not.toHaveBeenCalled();
  });

  it("deleting the only session falls back to the zero state", async () => {
    listAdventures.mockResolvedValueOnce({ adventures: [] });
    listSavedGames.mockResolvedValueOnce({ sessions: [inProgressSession()] });
    deleteSession.mockResolvedValue({ status: "deleted", sessionId: "session-1" });
    const user = userEvent.setup();
    await renderHome();

    await user.click(screen.getByRole("button", { name: /delete this session/i }));
    await user.click(await screen.findByRole("button", { name: /^delete$/i }));

    expect(await screen.findByText(/nothing on the go right now/i)).toBeInTheDocument();
    expect(screen.getByText(/when you open a story it lands here/i)).toBeInTheDocument();
  });
});
