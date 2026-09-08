import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

const acquireTokenSilent = vi.fn();
const createEditDraft = vi.fn();
const saveDraftToStory = vi.fn();
const patchDraft = vi.fn();

const mockInstance = { acquireTokenSilent };
const mockAccounts = [{ homeAccountId: "home-1", username: "admin@example.com" }];

vi.mock("@azure/msal-react", () => ({
  useMsal: () => ({ instance: mockInstance, accounts: mockAccounts }),
}));

vi.mock("../../src/services/storyDraftService.js", () => ({
  createEditDraft: (...args) => createEditDraft(...args),
  saveDraftToStory: (...args) => saveDraftToStory(...args),
  patchDraft: (...args) => patchDraft(...args),
  getDraft: vi.fn(),
  createDraft: vi.fn(),
  generateStory: vi.fn(),
  suggestWorldPrompt: vi.fn(),
}));

import AdminStoryWizardPage from "../../src/pages/AdminStoryWizardPage.jsx";

const SEEDED_DRAFT = {
  id: "draft-1",
  sourceStoryId: "story-1",
  baseContentVersion: 3,
  name: "The Sunken Library",
  coverImageUrl: null,
  tone: null,
  readingLevel: null,
  sessionLengthMinutes: null,
  chapters: null,
  worldPrompt: "A flooded library beneath a coastal town.",
  rules: null,
  characterTypes: [{ name: "Archivist", description: "" }],
  completionCriteria: { maxDurationMinutes: null, successConditions: ["Recover the ledger"], failureConditions: [], rule: null },
};

const renderEditPage = () =>
  render(
    <MemoryRouter initialEntries={["/admin/stories/story-1/edit"]}>
      <Routes>
        <Route path="/admin/stories/:storyId/edit" element={<AdminStoryWizardPage />} />
      </Routes>
    </MemoryRouter>,
  );

describe("Admin story edit flow (FR-003, FR-006)", () => {
  beforeEach(() => {
    acquireTokenSilent.mockReset().mockResolvedValue({ accessToken: "tok" });
    createEditDraft.mockReset();
    saveDraftToStory.mockReset();
    patchDraft.mockReset();
  });

  it("reopens a story in the wizard pre-filled from an edit draft", async () => {
    createEditDraft.mockResolvedValueOnce({ status: "success", draft: SEEDED_DRAFT, readyToGenerate: true });

    renderEditPage();

    expect(await screen.findByRole("heading", { name: /edit story/i })).toBeInTheDocument();
    expect(createEditDraft).toHaveBeenCalledWith("tok", "story-1");
    expect(await screen.findByRole("button", { name: /save changes/i })).toBeInTheDocument();
  });

  it("Save changes calls saveDraftToStory and shows the saved story", async () => {
    createEditDraft.mockResolvedValueOnce({ status: "success", draft: SEEDED_DRAFT, readyToGenerate: true });
    saveDraftToStory.mockResolvedValueOnce({
      status: "saved",
      storyId: "story-1",
      story: { id: "story-1", name: "The Sunken Library", narrativeGuidance: "Fresh guidance.", published: false, contentVersion: 4 },
    });

    renderEditPage();
    const saveButton = await screen.findByRole("button", { name: /save changes/i });
    await userEvent.click(saveButton);

    expect(saveDraftToStory).toHaveBeenCalledWith("tok", "draft-1");
    expect(await screen.findByText(/story saved/i)).toBeInTheDocument();
    expect(screen.getByText("Fresh guidance.")).toBeInTheDocument();
  });

  it("shows the reload-and-reapply message on a 409 stale_story", async () => {
    createEditDraft.mockResolvedValueOnce({ status: "success", draft: SEEDED_DRAFT, readyToGenerate: true });
    saveDraftToStory.mockRejectedValueOnce({
      response: {
        status: 409,
        data: { error: "stale_story", message: "This story changed since you opened it. Reload it and reapply your change." },
      },
    });

    renderEditPage();
    const saveButton = await screen.findByRole("button", { name: /save changes/i });
    await userEvent.click(saveButton);

    expect(await screen.findByText(/reload it and reapply your change/i)).toBeInTheDocument();
  });
});
