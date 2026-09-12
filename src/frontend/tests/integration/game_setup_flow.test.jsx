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
const CHARACTER_TYPES = [
  { name: "Detective", description: "Sharp-eyed." },
  { name: "Ghost", description: "Already knows every room." },
];

/** Renders GamePage exactly as HomePage's Play action reaches it (028-home-page-redesign,
 * research.md Decision 4): a chosen adventure id in route state, never an in-page picker. */
function renderForAdventure(adventureId = "a1") {
  return render(
    <MemoryRouter initialEntries={[{ pathname: "/game", state: { adventureId } }]}>
      <GamePage />
    </MemoryRouter>,
  );
}

describe("Game setup flow (006-adventure-and-character-setup, narrowed by 028-home-page-redesign)", () => {
  beforeEach(() => {
    acquireTokenSilent.mockReset().mockResolvedValue({ accessToken: "tok" });
    getAdventure.mockReset().mockResolvedValue({ adventure: { id: "a1", name: ADVENTURE_NAME, characterTypes: CHARACTER_TYPES } });
    createSession.mockReset();
  });

  it("loads the chosen adventure's character types and shows name/type entry immediately (FR-003)", async () => {
    renderForAdventure();

    expect(await screen.findByText(ADVENTURE_NAME)).toBeInTheDocument();
    expect(await screen.findByLabelText(/character name/i)).toBeInTheDocument();
    expect(await screen.findByRole("radio", { name: /detective/i })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /ghost/i })).toBeInTheDocument();
  });

  it("blocks starting play and identifies missing fields when incomplete (FR-004, FR-005)", async () => {
    const user = userEvent.setup();
    renderForAdventure();

    await screen.findByLabelText(/character name/i);
    await user.click(screen.getByRole("button", { name: /start playing/i }));

    expect(await screen.findByText(/character name is required/i)).toBeInTheDocument();
    expect(screen.getByText(/select a character type/i)).toBeInTheDocument();
    expect(createSession).not.toHaveBeenCalled();
  });

  it("creates a play session and hands off into the play surface once name and type are valid (FR-004, Acceptance Scenario 5)", async () => {
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
    await user.click(await screen.findByRole("radio", { name: /detective/i }));
    await user.click(screen.getByRole("button", { name: /start playing/i }));

    expect(await screen.findByText(/the door creaks open/i)).toBeInTheDocument();
    expect(createSession).toHaveBeenCalledWith("tok", { adventureId: "a1", characterName: "Wren", characterType: "Detective" });
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
