import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("../../src/services/gameService.js", () => ({
  submitInteraction: vi.fn(),
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

describe("Autosave disclosure (008-core-gameplay, FR-017)", () => {
  it("shows the 'Autosaved after every turn' label on the play surface", () => {
    render(
      <PlayPage
        sessionId="session-1"
        storyName="The Lighthouse at Gullwing Cove"
        initialNarrative={OPENING_NARRATIVE}
        getToken={vi.fn()}
        onExit={vi.fn()}
      />,
    );

    expect(screen.getByText(/autosaved after every turn/i)).toBeInTheDocument();
  });
});
