import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const submitInteraction = vi.fn();

vi.mock("../../src/services/gameService.js", () => ({
  submitInteraction: (...args) => submitInteraction(...args),
  resumeSession: vi.fn(),
}));

import PlayPage from "../../src/pages/PlayPage.jsx";

const OPENING_NARRATIVE = {
  turnNumber: 0,
  narrativeText: "The lighthouse door creaks open.",
  suggestedActions: ["look around"],
  locationLabel: "Lighthouse entrance",
  goalLabel: null,
  progress: null,
};

const renderPlayPage = () =>
  render(
    <PlayPage
      sessionId="session-1"
      storyName="The Lighthouse at Gullwing Cove"
      initialNarrative={OPENING_NARRATIVE}
      getToken={vi.fn().mockResolvedValue("tok")}
      onExit={vi.fn()}
    />,
  );

describe("Autosave disclosure (008-core-gameplay, FR-017, SC-014)", () => {
  beforeEach(() => {
    submitInteraction.mockReset();
  });

  it("shows the 'Autosaved after every turn' label on the play surface", () => {
    renderPlayPage();

    expect(screen.getByText(/autosaved after every turn/i)).toBeInTheDocument();
  });

  it("keeps the label visible after further turns", async () => {
    submitInteraction.mockResolvedValue({
      status: "active",
      narrative: {
        turnNumber: 1,
        narrativeText: "A spiral of stairs climbs into the dark.",
        suggestedActions: ["climb"],
        locationLabel: "Lighthouse base",
        goalLabel: null,
        progress: null,
      },
    });
    const user = userEvent.setup();
    renderPlayPage();

    await user.type(screen.getByLabelText(/what do you do next/i), "look around");
    await user.click(screen.getByRole("button", { name: /^go$/i }));

    expect(await screen.findByText(/a spiral of stairs/i)).toBeInTheDocument();
    expect(screen.getByText(/autosaved after every turn/i)).toBeInTheDocument();
  });

  it("keeps the label visible once the session has concluded", async () => {
    submitInteraction.mockResolvedValue({
      status: "concluded",
      narrative: {
        turnNumber: 1,
        narrativeText: "You escape the cove.",
        suggestedActions: [],
        locationLabel: "The shore",
        goalLabel: null,
        progress: null,
      },
      completionReason: { type: "success", detail: "the player escaped the cove" },
    });
    const user = userEvent.setup();
    renderPlayPage();

    await user.type(screen.getByLabelText(/what do you do next/i), "escape");
    await user.click(screen.getByRole("button", { name: /^go$/i }));

    expect(await screen.findByText(/this story has ended/i)).toBeInTheDocument();
    expect(screen.getByText(/autosaved after every turn/i)).toBeInTheDocument();
  });
});
