import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const acquireTokenSilent = vi.fn();
const createDraft = vi.fn();
const patchDraft = vi.fn();
const postMessage = vi.fn();
const generateStory = vi.fn();

const mockInstance = { acquireTokenSilent };
const mockAccounts = [{ homeAccountId: "home-1", username: "admin@example.com" }];

vi.mock("@azure/msal-react", () => ({
  useMsal: () => ({ instance: mockInstance, accounts: mockAccounts }),
}));

vi.mock("../../src/services/storyDraftService.js", () => ({
  createDraft: (...args) => createDraft(...args),
  patchDraft: (...args) => patchDraft(...args),
  postMessage: (...args) => postMessage(...args),
  generateStory: (...args) => generateStory(...args),
}));

import AdminStoryWizardPage from "../../src/pages/AdminStoryWizardPage.jsx";

const EMPTY_DRAFT = {
  id: "draft-1",
  name: null,
  coverImageUrl: null,
  tone: null,
  readingLevel: null,
  sessionLengthMinutes: null,
  chapters: null,
  worldPrompt: null,
  rules: null,
  characterTypes: [],
  completionCriteria: null,
  exchanges: [],
};

describe("Admin story creation: empty draft through generated, unpublished story", () => {
  beforeEach(() => {
    acquireTokenSilent.mockReset().mockResolvedValue({ accessToken: "tok" });
    createDraft.mockReset();
    patchDraft.mockReset();
    postMessage.mockReset();
    generateStory.mockReset();
  });

  it("starts a blank draft, answers the guiding question, fills in the dedicated fields, and only generates on the explicit action (#33)", async () => {
    createDraft.mockResolvedValueOnce({ draft: EMPTY_DRAFT });
    render(<AdminStoryWizardPage />);

    // Wait for the loaded wizard specifically — the loading placeholder ("Starting a
    // new story…") also matches a plain /new story/i query, which can race against it.
    expect(await screen.findByRole("tablist")).toBeInTheDocument();

    // The "Generate story" action is disabled until the draft is complete.
    expect(screen.getByRole("button", { name: /generate story/i })).toBeDisabled();

    // Fill in the story name (Name & cover, the default first tab) — required to
    // generate (revised 2026-08-31), independently of World & setting's own fields.
    patchDraft.mockResolvedValueOnce({
      status: "success",
      draft: { ...EMPTY_DRAFT, name: "The Lighthouse at Gullwing Cove" },
      readyToGenerate: false,
    });
    await userEvent.type(screen.getByLabelText(/story name/i), "The Lighthouse at Gullwing Cove");
    await userEvent.click(screen.getByRole("button", { name: /^save$/i }));

    expect(patchDraft).toHaveBeenCalledWith("tok", "draft-1", { name: "The Lighthouse at Gullwing Cove", coverImageUrl: "" });
    expect(screen.getByRole("button", { name: /generate story/i })).toBeDisabled();

    // Move to the World & setting step and answer the guiding question.
    await userEvent.click(screen.getByRole("tab", { name: /world & setting/i }));
    postMessage.mockResolvedValueOnce({
      status: "success",
      draft: {
        ...EMPTY_DRAFT,
        name: "The Lighthouse at Gullwing Cove",
        worldPrompt: "A half-abandoned lighthouse...",
        exchanges: [{ role: "administrator", message: "A half-abandoned lighthouse...", timestamp: "t" }],
      },
      readyToGenerate: false,
    });
    await userEvent.type(screen.getByPlaceholderText(/describe your idea/i), "A half-abandoned lighthouse...");
    await userEvent.click(screen.getByRole("button", { name: /send/i }));

    expect(await screen.findByText(/A half-abandoned lighthouse/, { selector: "p" })).toBeInTheDocument();
    expect(postMessage).toHaveBeenCalledWith("tok", "draft-1", "A half-abandoned lighthouse...");

    // Add a character type — not yet complete. Uses a persistent mock (not "once")
    // because blurring the still-focused description field again later (e.g. by
    // clicking elsewhere) harmlessly re-commits the same row.
    patchDraft.mockResolvedValue({
      status: "success",
      draft: {
        ...EMPTY_DRAFT,
        name: "The Lighthouse at Gullwing Cove",
        worldPrompt: "A half-abandoned lighthouse...",
        characterTypes: [{ name: "Curious Cousin", description: "" }],
      },
      readyToGenerate: false,
    });
    await userEvent.click(screen.getByRole("button", { name: /add character type/i }));
    await userEvent.type(screen.getByLabelText(/character name/i), "Curious Cousin");
    await userEvent.tab();

    expect(patchDraft).toHaveBeenCalledWith("tok", "draft-1", { characterTypes: [{ name: "Curious Cousin", description: "" }] });
    expect(screen.getByRole("button", { name: /generate story/i })).toBeDisabled();

    // Move focus away from the character-type row entirely before wiring up the
    // completing write, so its response isn't consumed by a stray re-commit of the
    // still-focused description field instead.
    await userEvent.click(screen.getByRole("heading", { name: /new story/i }));
    patchDraft.mockReset();

    // Add the completion criteria — this write completes the draft, but per #33 it
    // must only report readyToGenerate: true, never generate or navigate by itself.
    patchDraft.mockResolvedValueOnce({
      status: "success",
      draft: {
        ...EMPTY_DRAFT,
        name: "The Lighthouse at Gullwing Cove",
        worldPrompt: "A half-abandoned lighthouse...",
        characterTypes: [{ name: "Curious Cousin", description: "" }],
        completionCriteria: { maxDurationMinutes: null, successConditions: ["Find the keeper"], failureConditions: [], rule: null },
      },
      readyToGenerate: true,
    });
    await userEvent.click(screen.getByRole("button", { name: /add success condition/i }));
    await userEvent.type(screen.getByLabelText(/success condition/i), "Find the keeper");
    await userEvent.tab();

    // Still on the wizard — no wizard tabs disappear and nothing was generated yet.
    expect(screen.getByRole("tablist")).toBeInTheDocument();
    expect(generateStory).not.toHaveBeenCalled();

    const generateButton = await screen.findByRole("button", { name: /generate story/i });
    expect(generateButton).toBeEnabled();

    generateStory.mockResolvedValueOnce({
      status: "generated",
      storyId: "story-1",
      story: {
        id: "story-1",
        name: "The Lighthouse at Gullwing Cove",
        worldPrompt: "A half-abandoned lighthouse...",
        characterTypes: [{ name: "Curious Cousin", description: "" }],
        completionCriteria: { maxDurationMinutes: null, successConditions: ["Find the keeper"], failureConditions: [], rule: null },
        narrativeGuidance: "Keep it eerie but never actually dangerous.",
        published: false,
        createdAt: "2026-08-29T20:04:00Z",
      },
    });
    await userEvent.click(generateButton);

    expect(generateStory).toHaveBeenCalledWith("tok", "draft-1");
    expect(await screen.findByText(/story generated/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /the lighthouse at gullwing cove/i })).toBeInTheDocument();
    expect(screen.getByText(/keep it eerie but never actually dangerous/i)).toBeInTheDocument();
    expect(screen.getByText(/unpublished/i)).toBeInTheDocument();

    // No wizard step tabs or "save" control remain — the story is already persisted.
    expect(screen.queryByRole("tablist")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^save/i })).not.toBeInTheDocument();
  });

  it("shows a rejected PATCH's reason next to the field that caused it, not a generic banner", async () => {
    createDraft.mockResolvedValueOnce({
      draft: {
        ...EMPTY_DRAFT,
        worldPrompt: "A half-abandoned lighthouse...",
        characterTypes: [{ name: "Curious Cousin", description: "" }],
        completionCriteria: { maxDurationMinutes: null, successConditions: ["Find the keeper"], failureConditions: [], rule: null },
      },
    });
    render(<AdminStoryWizardPage />);
    await userEvent.click(await screen.findByRole("tab", { name: /world & setting/i }));

    // The backend rejects this write (e.g. a stale rule value after some other edit) with
    // its usual "<field>: <reason>" DraftValidationError shape.
    patchDraft.mockRejectedValueOnce({
      response: { data: { error: "invalid_field", message: "completionCriteria: rule is required when more than one condition is defined" } },
    });
    await userEvent.click(screen.getByRole("button", { name: /add failure condition/i }));
    await userEvent.type(screen.getByLabelText(/failure condition/i), "Leave the cove");
    await userEvent.tab();

    // The message is specific to the field and its actual reason — not a generic
    // "could not save" banner unrelated to what went wrong.
    expect(await screen.findByText(/rule is required when more than one condition is defined/i)).toBeInTheDocument();
    expect(screen.queryByText(/could not save/i)).not.toBeInTheDocument();
  });
});
