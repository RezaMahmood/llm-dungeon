/**
 * The play surface rendered inside the real `/game` layout (008-core-gameplay-done).
 *
 * The other Play tests render `PlayPage` on its own, which cannot see the header
 * `AuthenticatedLayout` supplies — exactly the blind spot that let a second, unconfirmed
 * "Pause & exit" ship. FR-016/SC-013 require every exit from an active session to pass
 * through the pause confirmation, so this suite asserts against the composed screen.
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@azure/msal-react", () => ({
  useMsal: () => ({
    instance: { logoutRedirect: vi.fn() },
    accounts: [{ name: "Ada B.", username: "ada@example.test" }],
  }),
}));

vi.mock("../../src/hooks/useCapabilities.js", () => ({
  useCapabilities: () => ({
    hasPlayer: true,
    hasAdministrator: false,
    loading: false,
    error: null,
    denied: false,
    refetch: vi.fn(),
  }),
}));

const submitInteraction = vi.fn();
const resumeSession = vi.fn();

vi.mock("../../src/services/gameService.js", () => ({
  submitInteraction: (...args) => submitInteraction(...args),
  resumeSession: (...args) => resumeSession(...args),
}));

import AuthenticatedLayout from "../../src/components/Layout/AuthenticatedLayout.jsx";
import PlayPage from "../../src/pages/PlayPage.jsx";

const STORY_NAME = "The Lighthouse at Gullwing Cove";

const OPENING_NARRATIVE = {
  turnNumber: 0,
  narrativeText: "The lighthouse door creaks open.",
  suggestedActions: ["look around", "step inside"],
  locationLabel: "Lighthouse entrance",
  goalLabel: null,
  progress: null,
};

function renderPlaySurface() {
  const onExit = vi.fn();
  render(
    <MemoryRouter initialEntries={["/game"]}>
      <Routes>
        <Route path="/menu" element={<p>story select</p>} />
        <Route
          path="/game"
          element={
            <AuthenticatedLayout>
              <PlayPage
                sessionId="session-1"
                storyName={STORY_NAME}
                initialTurns={[OPENING_NARRATIVE]}
                getToken={vi.fn().mockResolvedValue("tok")}
                onExit={onExit}
              />
            </AuthenticatedLayout>
          }
        />
      </Routes>
    </MemoryRouter>,
  );
  return { onExit };
}

describe("Play surface inside the /game layout (FR-016, SC-013)", () => {
  beforeEach(() => {
    submitInteraction.mockReset();
    resumeSession.mockReset();
  });

  it("renders exactly one title bar, showing the story name", () => {
    renderPlaySurface();

    expect(screen.getAllByRole("button", { name: /pause & exit/i })).toHaveLength(1);
    expect(screen.getByText(STORY_NAME)).toBeInTheDocument();
  });

  it("routes the title bar's exit action through the pause confirmation (FR-016)", async () => {
    const user = userEvent.setup();
    const { onExit } = renderPlaySurface();

    await user.click(screen.getByRole("button", { name: /pause & exit/i }));

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText(/your story is saved/i)).toBeInTheDocument();
    expect(onExit).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: /save and exit/i }));
    expect(onExit).toHaveBeenCalled();
  });

  it("lets the player cancel out of the pause dialog and keep playing", async () => {
    const user = userEvent.setup();
    const { onExit } = renderPlaySurface();

    await user.click(screen.getByRole("button", { name: /pause & exit/i }));
    await user.click(screen.getByRole("button", { name: /keep playing/i }));

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(onExit).not.toHaveBeenCalled();
    expect(screen.getByLabelText(/what do you do next/i)).toBeInTheDocument();
  });

  it("leaves no way out of an active session that skips the confirmation (SC-013)", async () => {
    const user = userEvent.setup();
    renderPlaySurface();

    // The brand mark is the header's other route out, so while a session is active it
    // must confirm too rather than being a plain link to story select.
    expect(screen.queryByRole("link", { name: /llm dungeon/i })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /llm dungeon/i }));

    expect(screen.queryByText("story select")).not.toBeInTheDocument();
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("keeps the autosave disclosure visible on the composed screen (FR-017)", () => {
    renderPlaySurface();

    expect(screen.getAllByText(/autosaved after every turn/i)).toHaveLength(1);
  });
});
