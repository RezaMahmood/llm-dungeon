import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const acquireTokenSilent = vi.fn();
const createDraft = vi.fn();
const generateStory = vi.fn();
const publishStory = vi.fn();
const unpublishStory = vi.fn();

const mockInstance = { acquireTokenSilent };
const mockAccounts = [{ homeAccountId: "home-1", username: "admin@example.com" }];

vi.mock("@azure/msal-react", () => ({
  useMsal: () => ({ instance: mockInstance, accounts: mockAccounts }),
}));

vi.mock("../../src/services/storyDraftService.js", () => ({
  createDraft: (...args) => createDraft(...args),
  generateStory: (...args) => generateStory(...args),
  publishStory: (...args) => publishStory(...args),
  unpublishStory: (...args) => unpublishStory(...args),
}));

import AdminStoryWizardPage from "../../src/pages/AdminStoryWizardPage.jsx";

const READY_DRAFT = {
  id: "draft-1",
  name: "The Lighthouse at Gullwing Cove",
  coverImageUrl: null,
  tone: null,
  readingLevel: null,
  sessionLengthMinutes: null,
  chapters: null,
  worldPrompt: "A half-abandoned lighthouse...",
  rules: null,
  characterTypes: [{ name: "Curious Cousin", description: "" }],
  completionCriteria: { maxDurationMinutes: null, successConditions: ["Find the keeper"], failureConditions: [], rule: null },
  exchanges: [],
};

const GENERATED_STORY = {
  id: "story-1",
  name: "The Lighthouse at Gullwing Cove",
  narrativeGuidance: "Keep it eerie but never actually dangerous.",
  published: false,
  lastPublishedAt: null,
};

async function renderGeneratedStory() {
  createDraft.mockResolvedValueOnce({ draft: READY_DRAFT });
  generateStory.mockResolvedValueOnce({ status: "generated", storyId: "story-1", story: GENERATED_STORY });
  render(<AdminStoryWizardPage />);

  const generateButton = await screen.findByRole("button", { name: /generate story/i });
  await userEvent.click(generateButton);
  expect(await screen.findByText(/story generated/i)).toBeInTheDocument();
}

describe("Admin story publish flow: generate -> blocked publish -> publish -> unpublish -> re-publish", () => {
  beforeEach(() => {
    acquireTokenSilent.mockReset().mockResolvedValue({ accessToken: "tok" });
    createDraft.mockReset();
    generateStory.mockReset();
    publishStory.mockReset();
    unpublishStory.mockReset();
  });

  it("walks the full publish/unpublish lifecycle (quickstart.md Scenarios 1-3)", async () => {
    await renderGeneratedStory();

    // Scenario 1: publish is blocked without a qualifying test play (FR-008, FR-011).
    publishStory.mockRejectedValueOnce({
      response: {
        status: 409,
        data: {
          error: "test_play_required",
          message: "This story must be test-played since its last content change before it can be published.",
        },
      },
    });
    await userEvent.click(screen.getByRole("button", { name: /^publish$/i }));
    expect(await screen.findByText(/must be test-played/i)).toBeInTheDocument();
    expect(screen.getByText(/unpublished/i)).toBeInTheDocument();

    // Scenario 2: publish succeeds once the gate is satisfied.
    publishStory.mockResolvedValueOnce({
      status: "success",
      story: { ...GENERATED_STORY, published: true, lastPublishedAt: "2026-08-30T14:22:00Z" },
    });
    await userEvent.click(screen.getByRole("button", { name: /^publish$/i }));
    expect(await screen.findByText(/^published$/i)).toBeInTheDocument();

    // Unpublish requires confirmation (FR-013).
    await userEvent.click(screen.getByRole("button", { name: /^unpublish$/i }));
    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveTextContent(/are you sure/i);
    expect(unpublishStory).not.toHaveBeenCalled();

    unpublishStory.mockResolvedValueOnce({
      status: "success",
      story: { ...GENERATED_STORY, published: false, lastPublishedAt: "2026-08-30T14:22:00Z" },
    });
    await userEvent.click(within(dialog).getByRole("button", { name: /^unpublish$/i }));

    expect(await screen.findByText(/unpublished/i)).toBeInTheDocument();

    // Scenario 3: republishing is idempotent.
    publishStory.mockResolvedValueOnce({
      status: "success",
      story: { ...GENERATED_STORY, published: true, lastPublishedAt: "2026-08-30T15:00:00Z" },
    });
    await userEvent.click(screen.getByRole("button", { name: /^publish$/i }));
    expect(await screen.findByText(/^published$/i)).toBeInTheDocument();
  });
});
