import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

const acquireTokenSilent = vi.fn();
const getStory = vi.fn();
const publishStory = vi.fn();
const startTestPlay = vi.fn();
const submitTestPlayInstruction = vi.fn();

const mockInstance = { acquireTokenSilent };
const mockAccounts = [{ homeAccountId: "home-1", username: "admin@example.com" }];

vi.mock("@azure/msal-react", () => ({
  useMsal: () => ({ instance: mockInstance, accounts: mockAccounts }),
}));

vi.mock("../../src/services/storyDraftService.js", () => ({
  getStory: (...args) => getStory(...args),
  publishStory: (...args) => publishStory(...args),
  unpublishStory: vi.fn(),
}));

vi.mock("../../src/services/testPlayService.js", () => ({
  startTestPlay: (...args) => startTestPlay(...args),
  submitTestPlayInstruction: (...args) => submitTestPlayInstruction(...args),
  deleteTestPlaySession: vi.fn(),
  getTestPlaySession: vi.fn(),
}));

import AdminStoryTestPlayPage from "../../src/pages/AdminStoryTestPlayPage.jsx";

const STORY = {
  id: "story-1",
  name: "The Lighthouse at Gullwing Cove",
  published: false,
  lastPublishedAt: null,
};

const OPENING_NARRATIVE = {
  turnNumber: 0,
  narrativeText: "The lighthouse door creaks open.",
  suggestedActions: ["look around", "step inside"],
  locationLabel: "Lighthouse entrance",
  goalLabel: null,
  progress: null,
};

const CONCLUDING_TURN = {
  turnNumber: 1,
  narrativeText: "You find the keeper at last.",
  suggestedActions: [],
  locationLabel: "Lighthouse top",
  goalLabel: "Find the keeper",
  progress: { current: 1, total: 1 },
};

function renderPage(extraRoutes = []) {
  return render(
    <MemoryRouter initialEntries={["/admin/stories/story-1/test-play"]}>
      <Routes>
        <Route path="/admin/stories/:storyId/test-play" element={<AdminStoryTestPlayPage />} />
        {extraRoutes}
      </Routes>
    </MemoryRouter>,
  );
}

async function reachConclusion(extraRoutes = []) {
  getStory.mockResolvedValueOnce({ status: "success", story: STORY });
  startTestPlay.mockResolvedValueOnce({
    status: "success",
    sessionId: "session-1",
    characterType: "Curious Cousin",
    narrative: OPENING_NARRATIVE,
  });
  submitTestPlayInstruction.mockResolvedValueOnce({
    status: "concluded",
    narrative: CONCLUDING_TURN,
    completionReason: { type: "success", detail: "Find the keeper" },
  });

  renderPage(extraRoutes);
  await screen.findByText(OPENING_NARRATIVE.narrativeText);

  await userEvent.type(screen.getByLabelText(/what do you do next/i), "search for the keeper");
  await userEvent.click(screen.getByRole("button", { name: /^go$/i }));

  await screen.findByRole("heading", { name: /playthrough concluded/i });
}

describe("Admin test-play conclusion flow (010-story-test-play FR-006, FR-007, FR-008)", () => {
  beforeEach(() => {
    acquireTokenSilent.mockReset().mockResolvedValue({ accessToken: "tok" });
    getStory.mockReset();
    publishStory.mockReset();
    startTestPlay.mockReset();
    submitTestPlayInstruction.mockReset();
  });

  it("publish from conclusion: confirm, then navigate to the story list (FR-007)", async () => {
    await reachConclusion([<Route key="admin" path="/admin" element={<div>Story list page</div>} />]);
    publishStory.mockResolvedValueOnce({
      status: "success",
      story: { ...STORY, published: true, lastPublishedAt: "2026-09-08T00:00:00Z" },
    });

    await userEvent.click(screen.getByRole("button", { name: /^publish$/i }));
    const dialog = screen.getByRole("dialog");
    await userEvent.click(within(dialog).getByRole("button", { name: /^publish$/i }));

    expect(publishStory).toHaveBeenCalledWith("tok", "story-1");
    expect(await screen.findByText(/story list page/i)).toBeInTheDocument();
  });

  it("edit from conclusion: returns to the wizard (FR-008)", async () => {
    await reachConclusion([<Route key="edit" path="/admin/stories/:storyId/edit" element={<div>Edit wizard page</div>} />]);

    await userEvent.click(screen.getByRole("button", { name: /return to the story wizard/i }));

    expect(await screen.findByText(/edit wizard page/i)).toBeInTheDocument();
  });

  it("a blocked publish stays on the conclusion screen with an explanation (edge case)", async () => {
    await reachConclusion();
    publishStory.mockRejectedValueOnce({
      response: {
        status: 409,
        data: { error: "test_play_required", message: "This story must be test-played since its last content change before it can be published." },
      },
    });

    await userEvent.click(screen.getByRole("button", { name: /^publish$/i }));
    const dialog = screen.getByRole("dialog");
    await userEvent.click(within(dialog).getByRole("button", { name: /^publish$/i }));

    expect(await screen.findByText(/must be test-played/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /playthrough concluded/i })).toBeInTheDocument();
  });
});
