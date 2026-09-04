import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const acquireTokenSilent = vi.fn();
const listAdventures = vi.fn();
const getAdventure = vi.fn();
const startGame = vi.fn();

const mockInstance = { acquireTokenSilent };
const mockAccounts = [{ homeAccountId: "home-1", username: "player@example.com" }];

vi.mock("@azure/msal-react", () => ({
  useMsal: () => ({ instance: mockInstance, accounts: mockAccounts }),
}));

vi.mock("../../src/services/gameService.js", () => ({
  listAdventures: (...args) => listAdventures(...args),
  getAdventure: (...args) => getAdventure(...args),
  startGame: (...args) => startGame(...args),
}));

import GamePage from "../../src/pages/GamePage.jsx";

const ADVENTURE = { id: "a1", name: "Nine Doors of Mudlark Hall", tone: "Mystery", sessionLengthMinutes: 20, readingLevel: "Year 5" };
const CHARACTER_TYPES = [
  { name: "Detective", description: "Sharp-eyed." },
  { name: "Ghost", description: "Already knows every room." },
];

describe("Game setup flow (006-adventure-and-character-setup)", () => {
  beforeEach(() => {
    acquireTokenSilent.mockReset().mockResolvedValue({ accessToken: "tok" });
    listAdventures.mockReset().mockResolvedValue({ adventures: [ADVENTURE] });
    getAdventure.mockReset().mockResolvedValue({ adventure: { id: "a1", name: ADVENTURE.name, characterTypes: CHARACTER_TYPES } });
    startGame.mockReset();
  });

  it("shows the empty-state message when no adventures are published (FR-006)", async () => {
    listAdventures.mockResolvedValue({ adventures: [] });

    render(<GamePage />);

    expect(await screen.findByText(/no adventures are published yet/i)).toBeInTheDocument();
  });

  it("hides character name and type steps until an adventure is selected (FR-003a)", async () => {
    render(<GamePage />);

    expect(await screen.findByText(ADVENTURE.name)).toBeInTheDocument();
    expect(screen.queryByLabelText(/character name/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/choose a character type/i)).not.toBeInTheDocument();
  });

  it("reveals name entry and that adventure's character types once selected (FR-003)", async () => {
    const user = userEvent.setup();
    render(<GamePage />);

    await user.click(await screen.findByText(ADVENTURE.name));

    expect(await screen.findByLabelText(/character name/i)).toBeInTheDocument();
    expect(await screen.findByRole("radio", { name: /detective/i })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /ghost/i })).toBeInTheDocument();
  });

  it("blocks starting play and identifies missing fields when incomplete (FR-004, FR-005)", async () => {
    const user = userEvent.setup();
    render(<GamePage />);

    await user.click(await screen.findByText(ADVENTURE.name));
    await user.click(screen.getByRole("button", { name: /start playing/i }));

    expect(await screen.findByText(/character name is required/i)).toBeInTheDocument();
    expect(screen.getByText(/select a character type/i)).toBeInTheDocument();
    expect(startGame).not.toHaveBeenCalled();
  });

  it("clears the chosen character type but keeps the name when the adventure changes (FR-004a)", async () => {
    const otherAdventure = { id: "a2", name: "The Balloon Post" };
    listAdventures.mockResolvedValue({ adventures: [ADVENTURE, otherAdventure] });
    getAdventure.mockImplementation((_token, id) =>
      id === "a1"
        ? Promise.resolve({ adventure: { id: "a1", name: ADVENTURE.name, characterTypes: CHARACTER_TYPES } })
        : Promise.resolve({ adventure: { id: "a2", name: otherAdventure.name, characterTypes: [{ name: "Pilot" }] } }),
    );

    const user = userEvent.setup();
    render(<GamePage />);

    await user.click(await screen.findByText(ADVENTURE.name));
    await user.type(await screen.findByLabelText(/character name/i), "Wren");
    await user.click(await screen.findByRole("radio", { name: /detective/i }));
    expect(screen.getByRole("radio", { name: /detective/i })).toBeChecked();

    await user.click(screen.getByText(otherAdventure.name));

    expect(await screen.findByRole("radio", { name: /pilot/i })).not.toBeChecked();
    expect(screen.getByLabelText(/character name/i)).toHaveValue("Wren");
  });

  it("ignores stale adventure detail responses after a newer selection", async () => {
    const otherAdventure = { id: "a2", name: "The Balloon Post" };
    listAdventures.mockResolvedValue({ adventures: [ADVENTURE, otherAdventure] });

    let resolveFirstAdventure;
    let resolveSecondAdventure;
    getAdventure.mockImplementation(
      (_token, id) =>
        new Promise((resolve) => {
          if (id === "a1") resolveFirstAdventure = resolve;
          if (id === "a2") resolveSecondAdventure = resolve;
        }),
    );

    const user = userEvent.setup();
    render(<GamePage />);

    await user.click(await screen.findByText(ADVENTURE.name));
    await user.click(screen.getByText(otherAdventure.name));

    resolveSecondAdventure({ adventure: { id: "a2", name: otherAdventure.name, characterTypes: [{ name: "Pilot" }] } });
    expect(await screen.findByRole("radio", { name: /pilot/i })).toBeInTheDocument();

    resolveFirstAdventure({ adventure: { id: "a1", name: ADVENTURE.name, characterTypes: CHARACTER_TYPES } });
    await waitFor(() => {
      expect(screen.queryByRole("radio", { name: /detective/i })).not.toBeInTheDocument();
      expect(screen.getByRole("radio", { name: /pilot/i })).toBeInTheDocument();
    });
  });

  it("starts the game once adventure, name, and type are all valid (FR-004, Acceptance Scenario 5)", async () => {
    startGame.mockResolvedValue({ status: "success", adventureId: "a1", characterName: "Wren", characterType: "Detective" });
    const user = userEvent.setup();
    render(<GamePage />);

    await user.click(await screen.findByText(ADVENTURE.name));
    await user.type(await screen.findByLabelText(/character name/i), "Wren");
    await user.click(await screen.findByRole("radio", { name: /detective/i }));
    await user.click(screen.getByRole("button", { name: /start playing/i }));

    expect(await screen.findByText(/playing as wren \(detective\)/i)).toBeInTheDocument();
    expect(startGame).toHaveBeenCalledWith("tok", { adventureId: "a1", characterName: "Wren", characterType: "Detective" });
  });
});
