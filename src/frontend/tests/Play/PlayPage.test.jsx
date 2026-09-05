import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const submitInteraction = vi.fn();
const resumeSession = vi.fn();

vi.mock("../../src/services/gameService.js", () => ({
  submitInteraction: (...args) => submitInteraction(...args),
  resumeSession: (...args) => resumeSession(...args),
}));

import PlayPage from "../../src/pages/PlayPage.jsx";

const OPENING_NARRATIVE = {
  turnNumber: 0,
  narrativeText: "The lighthouse door creaks open.",
  suggestedActions: ["look around", "step inside"],
  locationLabel: "Lighthouse entrance",
  goalLabel: null,
  progress: null,
};

function renderPlayPage(overrides = {}) {
  const getToken = vi.fn().mockResolvedValue("tok");
  const onExit = vi.fn();
  render(
    <PlayPage
      sessionId="session-1"
      storyName="The Lighthouse at Gullwing Cove"
      initialNarrative={OPENING_NARRATIVE}
      getToken={getToken}
      onExit={onExit}
      {...overrides}
    />,
  );
  return { getToken, onExit };
}

describe("PlayPage (008-core-gameplay)", () => {
  beforeEach(() => {
    submitInteraction.mockReset();
    resumeSession.mockReset();
  });

  it("renders the opening narrative after session creation", () => {
    renderPlayPage();

    expect(screen.getByText(OPENING_NARRATIVE.narrativeText)).toBeInTheDocument();
    expect(screen.getByText("Lighthouse entrance")).toBeInTheDocument();
  });

  it("appends the new turn after a free-text submit", async () => {
    submitInteraction.mockResolvedValue({
      status: "active",
      narrative: {
        turnNumber: 1,
        narrativeText: "A spiral of stairs climbs into the dark.",
        suggestedActions: ["climb the stairs"],
        locationLabel: "Lighthouse base",
        goalLabel: null,
        progress: null,
      },
    });
    const user = userEvent.setup();
    renderPlayPage();

    await user.type(screen.getByLabelText(/what do you do next/i), "look around");
    await user.click(screen.getByRole("button", { name: /^go$/i }));

    expect(await screen.findByText("A spiral of stairs climbs into the dark.")).toBeInTheDocument();
    expect(submitInteraction).toHaveBeenCalledWith("tok", "session-1", "look around");
  });

  it("gates input and shows the ending when the session concludes", async () => {
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
    expect(screen.queryByLabelText(/what do you do next/i)).not.toBeInTheDocument();
  });

  it("shows an inline notice on a 429 without clearing the typed input", async () => {
    submitInteraction.mockRejectedValue({ response: { status: 429, data: { error: "rate_limited", message: "Slow down a little." } } });
    const user = userEvent.setup();
    renderPlayPage();

    await user.type(screen.getByLabelText(/what do you do next/i), "look around");
    await user.click(screen.getByRole("button", { name: /^go$/i }));

    expect(await screen.findByText(/slow down a little/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/what do you do next/i)).toHaveValue("look around");
  });

  it("shows a lockout notice and disables further input on 423", async () => {
    submitInteraction.mockRejectedValue({
      response: { status: 423, data: { error: "content_safety_lockout", message: "You're temporarily locked out." } },
    });
    const user = userEvent.setup();
    renderPlayPage();

    await user.type(screen.getByLabelText(/what do you do next/i), "something disallowed");
    await user.click(screen.getByRole("button", { name: /^go$/i }));

    expect(await screen.findByText(/temporarily locked out/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/what do you do next/i)).toBeDisabled();
  });
});
