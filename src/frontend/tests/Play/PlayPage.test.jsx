import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

const submitInteraction = vi.fn();
const resumeSession = vi.fn();
const saveCheckpoint = vi.fn();
const getSession = vi.fn();

vi.mock("../../src/services/gameService.js", () => ({
  submitInteraction: (...args) => submitInteraction(...args),
  resumeSession: (...args) => resumeSession(...args),
  saveCheckpoint: (...args) => saveCheckpoint(...args),
  getSession: (...args) => getSession(...args),
}));

import TitleBar from "../../src/components/Layout/TitleBar.jsx";
import { PlayTitleProvider } from "../../src/context/PlayTitleContext.jsx";
import { RefreshProvider } from "../../src/context/RefreshContext.jsx";
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
      initialTurns={[OPENING_NARRATIVE]}
      getToken={getToken}
      onExit={onExit}
      {...overrides}
    />,
  );
  return { getToken, onExit };
}

/** Renders PlayPage alongside the real TitleBar it publishes to, matching how
 * AuthenticatedLayout composes them (009-save-and-continue, 029's RefreshContext). */
function renderPlayPageWithTitleBar(overrides = {}) {
  const getToken = vi.fn().mockResolvedValue("tok");
  const onExit = vi.fn();
  render(
    <MemoryRouter>
      <RefreshProvider>
        <PlayTitleProvider>
          <TitleBar />
          <PlayPage
            sessionId="session-1"
            storyName="The Lighthouse at Gullwing Cove"
            initialTurns={[OPENING_NARRATIVE]}
            getToken={getToken}
            onExit={onExit}
            {...overrides}
          />
        </PlayTitleProvider>
      </RefreshProvider>
    </MemoryRouter>,
  );
  return { getToken, onExit };
}

describe("PlayPage (008-core-gameplay-done)", () => {
  beforeEach(() => {
    submitInteraction.mockReset();
    resumeSession.mockReset();
    saveCheckpoint.mockReset();
    getSession.mockReset();
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

  // --- 025-story-delete-done (FR-007, FR-008): story deleted / unpublished ---

  it("shows the specific deleted notice with a return-to-list action on a 404 story_deleted", async () => {
    submitInteraction.mockRejectedValue({
      response: {
        status: 404,
        data: {
          error: "story_deleted",
          message: "Story has been deleted. You can no longer continue this story.",
          promptReturnToList: true,
        },
      },
    });
    const user = userEvent.setup();
    const { onExit } = renderPlayPage();

    await user.type(screen.getByLabelText(/what do you do next/i), "look around");
    await user.click(screen.getByRole("button", { name: /^go$/i }));

    expect(await screen.findByText(/story has been deleted/i)).toBeInTheDocument();
    expect(screen.queryByText(/something went wrong/i)).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /return to your story list/i }));
    expect(onExit).toHaveBeenCalled();
  });

  it("shows the specific unpublished notice with a return-to-list action on a 409 story_unpublished", async () => {
    submitInteraction.mockRejectedValue({
      response: {
        status: 409,
        data: {
          error: "story_unpublished",
          message: "Story has been unpublished. You can no longer continue this story.",
          promptReturnToList: true,
        },
      },
    });
    const user = userEvent.setup();
    const { onExit } = renderPlayPage();

    await user.type(screen.getByLabelText(/what do you do next/i), "look around");
    await user.click(screen.getByRole("button", { name: /^go$/i }));

    expect(await screen.findByText(/story has been unpublished/i)).toBeInTheDocument();
    expect(screen.queryByText(/something went wrong/i)).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /return to your story list/i }));
    expect(onExit).toHaveBeenCalled();
  });

  // --- 009-save-and-continue (T013): resumed history ---

  it("renders every prior turn from initialTurns, and the status panel reflects the latest one", () => {
    const turn1 = {
      turnNumber: 1,
      playerInput: "step inside",
      narrativeText: "A spiral of stairs climbs into the dark.",
      suggestedActions: ["climb the stairs"],
      locationLabel: "Lighthouse base",
      goalLabel: "Find the keeper",
      progress: { current: 1, total: 5 },
    };
    renderPlayPage({ initialTurns: [OPENING_NARRATIVE, turn1] });

    expect(screen.getByText(OPENING_NARRATIVE.narrativeText)).toBeInTheDocument();
    expect(screen.getByText(turn1.narrativeText)).toBeInTheDocument();
    // Status panel shows the latest turn's location, not the opening one's.
    expect(screen.getByText("Lighthouse base")).toBeInTheDocument();
  });

  // --- 009-save-and-continue (T027): explicit checkpoint save ---

  it("renders an auto-dismissing status confirmation naming the location on a successful save", async () => {
    saveCheckpoint.mockResolvedValue({ checkpoint: { label: "Lighthouse entrance", turnNumber: 0, createdAt: "now" } });
    const user = userEvent.setup();
    renderPlayPageWithTitleBar();

    await user.click(screen.getByRole("button", { name: /save a checkpoint/i }));

    const notice = await screen.findByRole("status");
    expect(notice).toHaveTextContent(/checkpoint saved at lighthouse entrance/i);

    await waitFor(
      () => expect(screen.queryByText(/checkpoint saved at lighthouse entrance/i)).not.toBeInTheDocument(),
      { timeout: 6000 },
    );
  }, 10000);

  it("shows the non-blocking failure notice on a failed save and leaves the game playable", async () => {
    saveCheckpoint.mockRejectedValue(new Error("network error"));
    const user = userEvent.setup();
    renderPlayPageWithTitleBar();

    await user.click(screen.getByRole("button", { name: /save a checkpoint/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/couldn't record that checkpoint.*progress is safe/i);
    expect(screen.getByLabelText(/what do you do next/i)).not.toBeDisabled();
  });

  it("still exits via Save and exit to my stories when the save fails, passing a failure notice along", async () => {
    saveCheckpoint.mockRejectedValue(new Error("network error"));
    const user = userEvent.setup();
    const { onExit } = renderPlayPageWithTitleBar();

    await user.click(screen.getByRole("button", { name: /pause & exit/i }));
    await user.click(screen.getByRole("button", { name: /save and exit to my stories/i }));

    await waitFor(() => expect(onExit).toHaveBeenCalledOnce());
    expect(onExit).toHaveBeenCalledWith(expect.stringMatching(/couldn't record that checkpoint/i));
  });

  it("exits with no argument via Save and exit to my stories when the save succeeds", async () => {
    saveCheckpoint.mockResolvedValue({ checkpoint: { label: "Lighthouse entrance", turnNumber: 0, createdAt: "now" } });
    const user = userEvent.setup();
    const { onExit } = renderPlayPageWithTitleBar();

    await user.click(screen.getByRole("button", { name: /pause & exit/i }));
    await user.click(screen.getByRole("button", { name: /save and exit to my stories/i }));

    await waitFor(() => expect(onExit).toHaveBeenCalledWith());
  });

  // --- 029-play-surface-design-spec (T024, US3): header Refresh control ---

  it("re-fetches the session and replaces the transcript on a successful refresh (029, FR-009)", async () => {
    getSession.mockResolvedValue({
      status: "success",
      session: {
        sessionId: "session-1",
        turns: [
          OPENING_NARRATIVE,
          {
            turnNumber: 1,
            narrativeText: "A spiral of stairs climbs into the dark.",
            suggestedActions: ["climb the stairs"],
            locationLabel: "Lighthouse base",
            goalLabel: null,
            progress: null,
            playerInput: "step inside",
          },
        ],
        status: "active",
        completionReason: null,
      },
    });
    const user = userEvent.setup();
    renderPlayPageWithTitleBar();

    await user.click(screen.getByRole("button", { name: /^refresh$/i }));

    expect(getSession).toHaveBeenCalledWith("tok", "session-1");
    expect(await screen.findByText("A spiral of stairs climbs into the dark.")).toBeInTheDocument();
    expect(screen.getByText("Lighthouse base")).toBeInTheDocument();
  });

  it("leaves the transcript and any typed input untouched and shows a notice on a failed refresh (029, FR-010)", async () => {
    getSession.mockRejectedValue(new Error("network error"));
    const user = userEvent.setup();
    renderPlayPageWithTitleBar();

    await user.type(screen.getByLabelText(/what do you do next/i), "look around");
    await user.click(screen.getByRole("button", { name: /^refresh$/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/refresh/i);
    expect(screen.getByText(OPENING_NARRATIVE.narrativeText)).toBeInTheDocument();
    expect(screen.getByLabelText(/what do you do next/i)).toHaveValue("look around");
  });

  it("routes a deleted-story refresh failure to the same notice and exit action a deleted-story submit failure uses (029)", async () => {
    getSession.mockRejectedValue({
      response: {
        status: 404,
        data: { error: "story_deleted", message: "Story has been deleted. You can no longer continue this story." },
      },
    });
    const user = userEvent.setup();
    const { onExit } = renderPlayPageWithTitleBar();

    await user.click(screen.getByRole("button", { name: /^refresh$/i }));

    expect(await screen.findByText(/story has been deleted/i)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /return to your story list/i }));
    expect(onExit).toHaveBeenCalled();
  });

  it("routes an unpublished-story refresh failure the same way (029)", async () => {
    getSession.mockRejectedValue({
      response: {
        status: 409,
        data: {
          error: "story_unpublished",
          message: "Story has been unpublished. You can no longer continue this story.",
        },
      },
    });
    const user = userEvent.setup();
    renderPlayPageWithTitleBar();

    await user.click(screen.getByRole("button", { name: /^refresh$/i }));

    expect(await screen.findByText(/story has been unpublished/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /return to your story list/i })).toBeInTheDocument();
  });

  it("disables the refresh control while a submit is in flight, and Go/chips while a refresh is in flight (029)", async () => {
    let resolveSubmit;
    submitInteraction.mockReturnValue(new Promise((resolve) => (resolveSubmit = resolve)));
    let resolveRefresh;
    getSession.mockReturnValue(new Promise((resolve) => (resolveRefresh = resolve)));
    const user = userEvent.setup();
    renderPlayPageWithTitleBar();

    await user.type(screen.getByLabelText(/what do you do next/i), "look around");
    await user.click(screen.getByRole("button", { name: /^go$/i }));
    expect(screen.getByRole("button", { name: /^refresh$/i })).toBeDisabled();

    resolveSubmit({
      status: "active",
      narrative: { ...OPENING_NARRATIVE, turnNumber: 1 },
    });
    await waitFor(() => expect(screen.getByRole("button", { name: /^refresh$/i })).not.toBeDisabled());

    await user.click(screen.getByRole("button", { name: /^refresh$/i }));
    expect(screen.getByLabelText(/what do you do next/i)).toBeDisabled();

    resolveRefresh({
      status: "success",
      session: { sessionId: "session-1", turns: [OPENING_NARRATIVE], status: "active", completionReason: null },
    });
    await waitFor(() => expect(screen.getByLabelText(/what do you do next/i)).not.toBeDisabled());
  });
});

describe("PlayPage — the session itself has been removed (031 FR-012)", () => {
  const removed = {
    response: {
      status: 404,
      data: {
        error: "session_removed",
        message: "This session has been removed. You can start this story again from your home page.",
        promptReturnToList: true,
      },
    },
  };

  beforeEach(() => {
    submitInteraction.mockReset();
    resumeSession.mockReset();
    saveCheckpoint.mockReset();
    getSession.mockReset();
  });

  it("leaves on a submit rather than showing an in-place notice", async () => {
    submitInteraction.mockRejectedValue(removed);
    const onSessionRemoved = vi.fn();
    renderPlayPage({ onSessionRemoved });

    await userEvent.click(screen.getByRole("button", { name: "look around" }));

    await waitFor(() => expect(onSessionRemoved).toHaveBeenCalled());
    // D7: the player is taken to Home, not parked behind a notice with a button.
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /return to your story list/i })).not.toBeInTheDocument();
  });

  it("leaves on a checkpoint save instead of claiming the progress is safe", async () => {
    saveCheckpoint.mockRejectedValue(removed);
    const onSessionRemoved = vi.fn();
    renderPlayPageWithTitleBar({ onSessionRemoved });

    await userEvent.click(screen.getByRole("button", { name: /save a checkpoint/i }));

    await waitFor(() => expect(onSessionRemoved).toHaveBeenCalled());
    expect(screen.queryByText(/your progress is safe/i)).not.toBeInTheDocument();
  });

  it("leaves on a refresh", async () => {
    getSession.mockRejectedValue(removed);
    const onSessionRemoved = vi.fn();
    renderPlayPageWithTitleBar({ onSessionRemoved });

    await userEvent.click(screen.getByRole("button", { name: /refresh/i }));

    await waitFor(() => expect(onSessionRemoved).toHaveBeenCalled());
  });

  it("still shows the in-place story-deleted notice, which is a different thing", async () => {
    submitInteraction.mockRejectedValue({
      response: {
        status: 404,
        data: { error: "story_deleted", message: "Story has been deleted. You can no longer continue this story." },
      },
    });
    const onSessionRemoved = vi.fn();
    renderPlayPage({ onSessionRemoved });

    await userEvent.click(screen.getByRole("button", { name: "look around" }));

    expect(await screen.findByRole("button", { name: /return to your story list/i })).toBeInTheDocument();
    expect(onSessionRemoved).not.toHaveBeenCalled();
  });
});
