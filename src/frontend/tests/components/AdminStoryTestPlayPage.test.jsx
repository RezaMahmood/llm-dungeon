import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

const acquireTokenSilent = vi.fn();
const getStory = vi.fn();
const startTestPlay = vi.fn();
const submitTestPlayInstruction = vi.fn();
const deleteTestPlaySession = vi.fn();

const mockInstance = { acquireTokenSilent };
const mockAccounts = [{ homeAccountId: "home-1", username: "admin@example.com" }];

vi.mock("@azure/msal-react", () => ({
  useMsal: () => ({ instance: mockInstance, accounts: mockAccounts }),
}));

vi.mock("../../src/services/storyDraftService.js", () => ({
  getStory: (...args) => getStory(...args),
  publishStory: vi.fn(),
  unpublishStory: vi.fn(),
}));

vi.mock("../../src/services/testPlayService.js", () => ({
  startTestPlay: (...args) => startTestPlay(...args),
  submitTestPlayInstruction: (...args) => submitTestPlayInstruction(...args),
  deleteTestPlaySession: (...args) => deleteTestPlaySession(...args),
  getTestPlaySession: vi.fn(),
}));

import AdminStoryTestPlayPage from "../../src/pages/AdminStoryTestPlayPage.jsx";

const STORY = {
  id: "story-1",
  name: "The Lighthouse at Gullwing Cove",
  published: false,
  lastPublishedAt: null,
  lastTestPlayedAt: null,
};

const OPENING_NARRATIVE = {
  turnNumber: 0,
  narrativeText: "The lighthouse door creaks open.",
  suggestedActions: ["look around", "step inside"],
  locationLabel: "Lighthouse entrance",
  goalLabel: null,
  progress: null,
};

const NEXT_TURN = {
  turnNumber: 1,
  narrativeText: "You step inside.",
  suggestedActions: ["climb the stairs"],
  locationLabel: "Lighthouse foyer",
  goalLabel: "Find the keeper",
  progress: null,
};

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/admin/stories/story-1/test-play"]}>
      <Routes>
        <Route path="/admin/stories/:storyId/test-play" element={<AdminStoryTestPlayPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("AdminStoryTestPlayPage (010-story-test-play)", () => {
  beforeEach(() => {
    acquireTokenSilent.mockReset().mockResolvedValue({ accessToken: "tok" });
    getStory.mockReset();
    startTestPlay.mockReset();
    submitTestPlayInstruction.mockReset();
    deleteTestPlaySession.mockReset();
  });

  it("starts a test-play session and marks it as test/draft in text (FR-003)", async () => {
    getStory.mockResolvedValueOnce({ status: "success", story: STORY });
    startTestPlay.mockResolvedValueOnce({
      status: "success",
      sessionId: "session-1",
      characterType: "Curious Cousin",
      narrative: OPENING_NARRATIVE,
    });

    renderPage();

    expect(await screen.findByText(OPENING_NARRATIVE.narrativeText)).toBeInTheDocument();
    expect(screen.getByText(/test play/i)).toBeInTheDocument();
    expect(screen.getByText(/draft, not published/i)).toBeInTheDocument();
    expect(startTestPlay).toHaveBeenCalledWith("tok", "story-1");
  });

  it("restart shows a warning before anything happens; dismissing leaves the conversation intact (FR-005)", async () => {
    getStory.mockResolvedValueOnce({ status: "success", story: STORY });
    startTestPlay.mockResolvedValueOnce({
      status: "success",
      sessionId: "session-1",
      characterType: "Curious Cousin",
      narrative: OPENING_NARRATIVE,
    });

    renderPage();
    await screen.findByText(OPENING_NARRATIVE.narrativeText);

    await userEvent.click(screen.getByRole("button", { name: /restart/i }));

    const dialog = screen.getByRole("dialog");
    expect(dialog).toBeInTheDocument();
    expect(deleteTestPlaySession).not.toHaveBeenCalled();

    await userEvent.click(screen.getByRole("button", { name: /keep playing/i }));

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(deleteTestPlaySession).not.toHaveBeenCalled();
    expect(screen.getByText(OPENING_NARRATIVE.narrativeText)).toBeInTheDocument();
  });

  it("restart confirmed deletes the session and navigates to the edit page (FR-005)", async () => {
    getStory.mockResolvedValueOnce({ status: "success", story: STORY });
    startTestPlay.mockResolvedValueOnce({
      status: "success",
      sessionId: "session-1",
      characterType: "Curious Cousin",
      narrative: OPENING_NARRATIVE,
    });
    deleteTestPlaySession.mockResolvedValueOnce({ status: "deleted", sessionId: "session-1" });

    render(
      <MemoryRouter initialEntries={["/admin/stories/story-1/test-play"]}>
        <Routes>
          <Route path="/admin/stories/:storyId/test-play" element={<AdminStoryTestPlayPage />} />
          <Route path="/admin/stories/:storyId/edit" element={<div>Edit story page</div>} />
        </Routes>
      </MemoryRouter>,
    );
    await screen.findByText(OPENING_NARRATIVE.narrativeText);

    await userEvent.click(screen.getByRole("button", { name: /restart/i }));
    const dialog = screen.getByRole("dialog");
    await userEvent.click(within(dialog).getByRole("button", { name: /^restart$/i }));

    await waitFor(() => expect(deleteTestPlaySession).toHaveBeenCalledWith("tok", "session-1"));
    expect(await screen.findByText(/edit story page/i)).toBeInTheDocument();
  });

  it("submitting an instruction renders the next turn", async () => {
    getStory.mockResolvedValueOnce({ status: "success", story: STORY });
    startTestPlay.mockResolvedValueOnce({
      status: "success",
      sessionId: "session-1",
      characterType: "Curious Cousin",
      narrative: OPENING_NARRATIVE,
    });
    submitTestPlayInstruction.mockResolvedValueOnce({ status: "active", narrative: NEXT_TURN });

    renderPage();
    await screen.findByText(OPENING_NARRATIVE.narrativeText);

    await userEvent.type(screen.getByLabelText(/what do you do next/i), "step inside");
    await userEvent.click(screen.getByRole("button", { name: /^go$/i }));

    expect(await screen.findByText(NEXT_TURN.narrativeText)).toBeInTheDocument();
    expect(submitTestPlayInstruction).toHaveBeenCalledWith("tok", "session-1", "step inside");
  });

  it("shows the conclusion screen when a response returns status concluded (FR-006)", async () => {
    getStory.mockResolvedValueOnce({ status: "success", story: STORY });
    startTestPlay.mockResolvedValueOnce({
      status: "success",
      sessionId: "session-1",
      characterType: "Curious Cousin",
      narrative: OPENING_NARRATIVE,
    });
    submitTestPlayInstruction.mockResolvedValueOnce({
      status: "concluded",
      narrative: NEXT_TURN,
      completionReason: { type: "success", detail: "Find the keeper" },
    });

    renderPage();
    await screen.findByText(OPENING_NARRATIVE.narrativeText);

    await userEvent.type(screen.getByLabelText(/what do you do next/i), "find the keeper");
    await userEvent.click(screen.getByRole("button", { name: /^go$/i }));

    expect(await screen.findByRole("heading", { name: /playthrough concluded/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^publish$/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /return to the story wizard/i })).toBeInTheDocument();

    // The concluding narrative — and the turn before it — must still be visible, not
    // discarded in favor of the bare summary (regression coverage for the bug where the
    // whole play screen was replaced on conclusion).
    expect(screen.getByText(OPENING_NARRATIVE.narrativeText)).toBeInTheDocument();
    expect(screen.getByText(NEXT_TURN.narrativeText)).toBeInTheDocument();
  });
});
