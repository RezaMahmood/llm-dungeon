import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

const acquireTokenSilent = vi.fn();
const getAdventure = vi.fn();
const createSession = vi.fn();

const mockInstance = { acquireTokenSilent };
const mockAccounts = [{ homeAccountId: "home-1", username: "player@example.com" }];

vi.mock("@azure/msal-react", () => ({
  useMsal: () => ({ instance: mockInstance, accounts: mockAccounts }),
}));

vi.mock("../../src/services/gameService.js", () => ({
  getAdventure: (...args) => getAdventure(...args),
  createSession: (...args) => createSession(...args),
  submitInteraction: vi.fn(),
  resumeSession: vi.fn(),
  getSession: vi.fn(),
}));

import GamePage from "../../src/pages/GamePage.jsx";

const ADVENTURE_NAME = "Nine Doors of Mudlark Hall";
const VALID_AVATAR_DESCRIPTION = "A one-eyed lighthouse keeper's apprentice who fears the dark.";

/** Renders GamePage exactly as HomePage's Play action reaches it (028-home-page-redesign,
 * research.md Decision 4): a chosen adventure id in route state, never an in-page picker. */
function renderForAdventure(adventureId = "a1") {
  return render(
    <MemoryRouter initialEntries={[{ pathname: "/game", state: { adventureId } }]}>
      <GamePage />
    </MemoryRouter>,
  );
}

describe("Game setup flow (032-story-archetypes-player-avatar, narrowed by 028-home-page-redesign)", () => {
  beforeEach(() => {
    acquireTokenSilent.mockReset().mockResolvedValue({ accessToken: "tok" });
    getAdventure.mockReset().mockResolvedValue({ adventure: { id: "a1", name: ADVENTURE_NAME } });
    createSession.mockReset();
  });

  it("loads the chosen adventure's name and shows name/avatar entry with no character-type choice (FR-002, FR-003, SC-003)", async () => {
    renderForAdventure();

    expect(await screen.findByText(ADVENTURE_NAME)).toBeInTheDocument();
    expect(await screen.findByLabelText(/character name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^describe your character$/i)).toBeInTheDocument();
    expect(screen.queryByRole("radio")).not.toBeInTheDocument();
  });

  it("blocks starting play and identifies missing fields when incomplete (FR-004)", async () => {
    const user = userEvent.setup();
    renderForAdventure();

    await screen.findByLabelText(/character name/i);
    await user.click(screen.getByRole("button", { name: /start playing/i }));

    expect(await screen.findByText(/character name is required/i)).toBeInTheDocument();
    expect(screen.getByText(/describe your character before you begin/i)).toBeInTheDocument();
    expect(createSession).not.toHaveBeenCalled();
  });

  it("creates a play session and hands off into the play surface once name and avatar description are valid (Acceptance Scenario 3)", async () => {
    createSession.mockResolvedValue({
      status: "success",
      sessionId: "session-1",
      narrative: {
        turnNumber: 0,
        narrativeText: "The door creaks open.",
        suggestedActions: ["look around", "step inside"],
        locationLabel: "Entrance",
        goalLabel: null,
        progress: null,
      },
    });
    const user = userEvent.setup();
    renderForAdventure();

    await user.type(await screen.findByLabelText(/character name/i), "Wren");
    await user.type(screen.getByLabelText(/^describe your character$/i), VALID_AVATAR_DESCRIPTION);
    await user.click(screen.getByRole("button", { name: /start playing/i }));

    expect(await screen.findByText(/the door creaks open/i)).toBeInTheDocument();
    expect(createSession).toHaveBeenCalledWith("tok", {
      adventureId: "a1",
      characterName: "Wren",
      avatarDescription: VALID_AVATAR_DESCRIPTION,
    });
  });

  it("identifies a too-short avatar description without calling the server (FR-006)", async () => {
    const user = userEvent.setup();
    renderForAdventure();

    await user.type(await screen.findByLabelText(/character name/i), "Wren");
    await user.type(screen.getByLabelText(/^describe your character$/i), "a knight");
    await user.click(screen.getByRole("button", { name: /start playing/i }));

    expect(await screen.findByText(/at least 20 characters/i)).toBeInTheDocument();
    expect(createSession).not.toHaveBeenCalled();
  });

  it("retains the character name and typed avatar text when the selected adventure changes (FR-005)", async () => {
    const { rerender } = renderForAdventure("a1");
    const user = userEvent.setup();

    await user.type(await screen.findByLabelText(/character name/i), "Wren");
    await user.type(screen.getByLabelText(/^describe your character$/i), VALID_AVATAR_DESCRIPTION);

    getAdventure.mockResolvedValue({ adventure: { id: "a2", name: "A Different Adventure" } });
    rerender(
      <MemoryRouter initialEntries={[{ pathname: "/game", state: { adventureId: "a2" } }]}>
        <GamePage />
      </MemoryRouter>,
    );

    expect(screen.getByLabelText(/character name/i)).toHaveValue("Wren");
    expect(screen.getByLabelText(/^describe your character$/i)).toHaveValue(VALID_AVATAR_DESCRIPTION);
  });

  it("prefills the avatar field from the player's stored description for this adventure (034 FR-006)", async () => {
    getAdventure.mockResolvedValue({
      adventure: { id: "a1", name: ADVENTURE_NAME, avatarDescription: "A returning lighthouse keeper." },
    });
    renderForAdventure();

    expect(await screen.findByLabelText(/^describe your character$/i)).toHaveValue("A returning lighthouse keeper.");
  });

  it("leaves the avatar field empty when the player has no stored description for this adventure (034 FR-007)", async () => {
    getAdventure.mockResolvedValue({ adventure: { id: "a1", name: ADVENTURE_NAME, avatarDescription: null } });
    renderForAdventure();

    await screen.findByText(ADVENTURE_NAME);
    expect(screen.getByLabelText(/^describe your character$/i)).toHaveValue("");
  });

  it("lets the player edit a prefilled description before starting (034 FR-006)", async () => {
    getAdventure.mockResolvedValue({
      adventure: { id: "a1", name: ADVENTURE_NAME, avatarDescription: "A returning lighthouse keeper." },
    });
    createSession.mockResolvedValue({
      status: "success",
      sessionId: "session-1",
      narrative: {
        turnNumber: 0,
        narrativeText: "The door creaks open.",
        suggestedActions: ["look"],
        locationLabel: "Entrance",
        goalLabel: null,
        progress: null,
      },
    });
    const user = userEvent.setup();
    renderForAdventure();

    const field = await screen.findByLabelText(/^describe your character$/i);
    expect(field).toHaveValue("A returning lighthouse keeper.");
    await user.type(field, " Now with a limp.");
    await user.type(await screen.findByLabelText(/character name/i), "Wren");
    await user.click(screen.getByRole("button", { name: /start playing/i }));

    expect(await screen.findByText(/the door creaks open/i)).toBeInTheDocument();
    expect(createSession).toHaveBeenCalledWith("tok", {
      adventureId: "a1",
      characterName: "Wren",
      avatarDescription: "A returning lighthouse keeper. Now with a limp.",
    });
  });

  it("redirects to Home when reached with no route state (research.md Decision 10)", async () => {
    render(
      <MemoryRouter initialEntries={["/game"]}>
        <GamePage />
      </MemoryRouter>,
    );

    expect(getAdventure).not.toHaveBeenCalled();
  });
});
