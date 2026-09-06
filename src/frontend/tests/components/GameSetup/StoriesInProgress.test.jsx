import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import StoriesInProgress from "../../../src/components/GameSetup/StoriesInProgress.jsx";

const SESSION_A = {
  sessionId: "s1",
  adventureId: "a1",
  adventureName: "The Lighthouse at Gullwing Cove",
  characterName: "Bramble",
  locationLabel: "The keeper's stairs",
  progress: { current: 3, total: 5 },
  turnCount: 12,
  startedAt: "2026-09-01T18:22:04Z",
  lastInteractionAt: "2026-09-05T20:11:47Z",
  isActiveForPlayer: true,
  checkpointCount: 2,
};

const SESSION_B = {
  sessionId: "s2",
  adventureId: "a2",
  adventureName: "Marsh of the Missing Bells",
  characterName: "Ash",
  locationLabel: "Outside the bell tower",
  progress: { current: 1, total: 4 },
  turnCount: 3,
  startedAt: "2026-08-20T10:00:00Z",
  lastInteractionAt: "2026-08-25T09:00:00Z",
  isActiveForPlayer: false,
  checkpointCount: 0,
};

describe("StoriesInProgress (009-save-and-continue, FR-001, FR-002)", () => {
  it("renders each row's adventure title, last-played time, and location", () => {
    render(<StoriesInProgress sessions={[SESSION_A]} loading={false} error={null} onResume={() => {}} />);

    expect(screen.getByText(/The Lighthouse at Gullwing Cove/)).toBeInTheDocument();
    expect(screen.getByText(/Last played/)).toBeInTheDocument();
    expect(screen.getByText(/The keeper's stairs/)).toBeInTheDocument();
  });

  it("renders rows in the order supplied", () => {
    render(<StoriesInProgress sessions={[SESSION_A, SESSION_B]} loading={false} error={null} onResume={() => {}} />);

    const titles = screen.getAllByText(/Gullwing Cove|Missing Bells/).map((el) => el.textContent);
    expect(titles[0]).toMatch(/Gullwing Cove/);
    expect(titles[1]).toMatch(/Missing Bells/);
  });

  it("marks the active game with text, not just styling (Principle VIII)", () => {
    render(<StoriesInProgress sessions={[SESSION_A, SESSION_B]} loading={false} error={null} onResume={() => {}} />);

    expect(screen.getByText("Current game")).toBeInTheDocument();
  });

  it("shows a saved indicator for a row with checkpointCount > 0", () => {
    render(<StoriesInProgress sessions={[SESSION_A]} loading={false} error={null} onResume={() => {}} />);

    expect(screen.getByText("Saved")).toBeInTheDocument();
  });

  it("does not show a saved indicator for a row with no checkpoints", () => {
    render(<StoriesInProgress sessions={[SESSION_B]} loading={false} error={null} onResume={() => {}} />);

    expect(screen.queryByText("Saved")).not.toBeInTheDocument();
  });

  it("renders the nothing-to-continue message, not an empty box, when there is nothing (FR-002)", () => {
    render(<StoriesInProgress sessions={[]} loading={false} error={null} onResume={() => {}} />);

    expect(screen.getByText(/nothing to continue/i)).toBeInTheDocument();
  });

  it("calls onResume with the clicked session", async () => {
    const onResume = vi.fn();
    const user = userEvent.setup();
    render(<StoriesInProgress sessions={[SESSION_A]} loading={false} error={null} onResume={onResume} />);

    await user.click(screen.getByRole("button", { name: /resume/i }));

    expect(onResume).toHaveBeenCalledWith(SESSION_A);
  });
});
