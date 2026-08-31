import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

const acquireTokenSilent = vi.fn();
const createStory = vi.fn();
const updateStory = vi.fn();
const deleteStory = vi.fn();
const suggestOutline = vi.fn();
const navigate = vi.fn();

const mockInstance = { acquireTokenSilent };
const mockAccounts = [{ homeAccountId: "home-1", username: "admin@example.com" }];

vi.mock("@azure/msal-react", () => ({
  useMsal: () => ({ instance: mockInstance, accounts: mockAccounts }),
}));

vi.mock("../../src/services/storyService.js", () => ({
  createStory: (...args) => createStory(...args),
  updateStory: (...args) => updateStory(...args),
  deleteStory: (...args) => deleteStory(...args),
  suggestOutline: (...args) => suggestOutline(...args),
  uploadCoverImage: vi.fn(),
}));

vi.mock("react-router-dom", async (importOriginal) => {
  const actual = await importOriginal();
  return { ...actual, useNavigate: () => navigate };
});

import AdminStoryWizardPage from "../../src/pages/AdminStoryWizardPage.jsx";

const DRAFT_STORAGE_KEY = "llmdungeon.storyWizard.draft";

const renderWizard = () =>
  render(
    <MemoryRouter initialEntries={["/admin/stories/new"]}>
      <AdminStoryWizardPage />
    </MemoryRouter>,
  );

describe("Story creation wizard — explicit Save, Abandon, Finished, and local-storage draft", () => {
  beforeEach(() => {
    localStorage.clear();
    acquireTokenSilent.mockReset().mockResolvedValue({ accessToken: "tok" });
    createStory.mockReset();
    updateStory.mockReset();
    deleteStory.mockReset();
    suggestOutline.mockReset();
    navigate.mockReset();
  });

  // --- User Story 2: tab navigation never loses unsaved input (FR-010) ---

  it("keeps field values entered on one tab intact after switching away and back, before any Save", async () => {
    const user = userEvent.setup();
    renderWizard();
    await screen.findByRole("tablist");

    await user.type(screen.getByLabelText(/^story name$/i), "The Lighthouse");

    await user.click(screen.getByRole("tab", { name: /world & setting/i }));
    await user.type(screen.getByLabelText(/^outline/i), "A half-abandoned lighthouse...");

    await user.click(screen.getByRole("tab", { name: /name & cover/i }));
    expect(screen.getByLabelText(/^story name$/i)).toHaveValue("The Lighthouse");

    await user.click(screen.getByRole("tab", { name: /world & setting/i }));
    expect(screen.getByLabelText(/^outline/i)).toHaveValue("A half-abandoned lighthouse...");

    // Nothing was sent to the backend by simply navigating tabs.
    expect(createStory).not.toHaveBeenCalled();
    expect(updateStory).not.toHaveBeenCalled();
  });

  it("survives a full page reload via local storage, before any Save", async () => {
    const user = userEvent.setup();
    const first = renderWizard();
    await screen.findByRole("tablist");

    await user.type(screen.getByLabelText(/^story name$/i), "The Lighthouse");
    await waitFor(() => expect(localStorage.getItem(DRAFT_STORAGE_KEY)).toContain("The Lighthouse"));

    first.unmount();
    renderWizard();
    await screen.findByRole("tablist");

    expect(screen.getByLabelText(/^story name$/i)).toHaveValue("The Lighthouse");
  });

  // --- User Story 1: Save creates then updates (FR-004) ---

  it("creates the story on the first Save, then updates the same record on a later Save", async () => {
    const user = userEvent.setup();
    createStory.mockResolvedValue({
      story: { id: "story-1", name: "The Lighthouse", outline: null, characterTypes: [], completionCriteria: null, published: false },
    });
    renderWizard();
    await screen.findByRole("tablist");

    await user.type(screen.getByLabelText(/^story name$/i), "The Lighthouse");
    await user.click(screen.getByRole("button", { name: /^save$/i }));

    await waitFor(() => expect(createStory).toHaveBeenCalledWith("tok", expect.objectContaining({ name: "The Lighthouse" })));
    expect(await screen.findByText(/^saved$/i)).toBeInTheDocument();

    updateStory.mockResolvedValue({
      story: {
        id: "story-1",
        name: "The Lighthouse",
        outline: "A half-abandoned lighthouse...",
        characterTypes: [],
        completionCriteria: null,
        published: false,
      },
    });
    await user.click(screen.getByRole("tab", { name: /world & setting/i }));
    await user.type(screen.getByLabelText(/^outline/i), "A half-abandoned lighthouse...");
    await user.click(screen.getByRole("button", { name: /^save$/i }));

    await waitFor(() => expect(updateStory).toHaveBeenCalledWith("tok", "story-1", expect.objectContaining({ outline: "A half-abandoned lighthouse..." })));
    expect(createStory).toHaveBeenCalledTimes(1); // never re-created
  });

  it("refuses to Save a brand-new story with no name", async () => {
    const user = userEvent.setup();
    renderWizard();
    await screen.findByRole("tablist");

    await user.click(screen.getByRole("button", { name: /^save$/i }));

    expect(await screen.findByText(/story name is required/i)).toBeInTheDocument();
    expect(createStory).not.toHaveBeenCalled();
  });

  // --- User Story 3: Abandon and Finished ---

  it("abandon: confirming deletes the persisted story and redirects; dismissing does nothing", async () => {
    const user = userEvent.setup();
    createStory.mockResolvedValue({ story: { id: "story-1", name: "The Lighthouse", characterTypes: [], completionCriteria: null } });
    deleteStory.mockResolvedValue({ status: "success" });
    renderWizard();
    await screen.findByRole("tablist");

    await user.type(screen.getByLabelText(/^story name$/i), "The Lighthouse");
    await user.click(screen.getByRole("button", { name: /^save$/i }));
    await waitFor(() => expect(createStory).toHaveBeenCalled());

    // Open the confirmation, then dismiss — nothing happens.
    await user.click(screen.getByRole("button", { name: /^abandon$/i }));
    await user.click(screen.getByRole("button", { name: /keep working/i }));
    expect(deleteStory).not.toHaveBeenCalled();
    expect(navigate).not.toHaveBeenCalled();

    // Open again and confirm this time.
    await user.click(screen.getByRole("button", { name: /^abandon$/i }));
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: /^abandon$/i }));

    await waitFor(() => expect(deleteStory).toHaveBeenCalledWith("tok", "story-1"));
    expect(navigate).toHaveBeenCalledWith("/admin");
    expect(localStorage.getItem(DRAFT_STORAGE_KEY)).toBeNull();
  });

  it("abandon on a never-saved session is a no-op delete, but still discards the draft and redirects", async () => {
    const user = userEvent.setup();
    renderWizard();
    await screen.findByRole("tablist");

    await user.type(screen.getByLabelText(/^story name$/i), "Unsaved idea");
    await user.click(screen.getByRole("button", { name: /^abandon$/i }));
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: /^abandon$/i }));

    await waitFor(() => expect(navigate).toHaveBeenCalledWith("/admin"));
    expect(deleteStory).not.toHaveBeenCalled();
    expect(localStorage.getItem(DRAFT_STORAGE_KEY)).toBeNull();
  });

  it("finished: confirming leaves saved data alone and redirects to the stories list", async () => {
    const user = userEvent.setup();
    createStory.mockResolvedValue({ story: { id: "story-1", name: "The Lighthouse", characterTypes: [], completionCriteria: null } });
    renderWizard();
    await screen.findByRole("tablist");

    await user.type(screen.getByLabelText(/^story name$/i), "The Lighthouse");
    await user.click(screen.getByRole("button", { name: /^save$/i }));
    await waitFor(() => expect(createStory).toHaveBeenCalled());

    await user.click(screen.getByRole("button", { name: /^finished$/i }));
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: /^finished$/i }));

    expect(deleteStory).not.toHaveBeenCalled();
    expect(navigate).toHaveBeenCalledWith("/admin");
  });

  // --- Tab 02 Suggest action (FR-003) ---

  it("suggest injects the returned outline into the editable outline box without a manual save step", async () => {
    const user = userEvent.setup();
    suggestOutline.mockResolvedValue({ outline: "A half-abandoned lighthouse on a cold northern cove." });
    renderWizard();
    await screen.findByRole("tablist");

    await user.click(screen.getByRole("tab", { name: /world & setting/i }));
    await user.type(screen.getByLabelText(/idea or guiding question/i), "a lighthouse mystery");
    await user.click(screen.getByRole("button", { name: /^suggest$/i }));

    expect(await screen.findByLabelText(/^outline/i)).toHaveValue("A half-abandoned lighthouse on a cold northern cove.");
  });

  it("suggest failure leaves the existing outline text untouched and surfaces the error", async () => {
    const user = userEvent.setup();
    suggestOutline.mockRejectedValue(new Error("boom"));
    renderWizard();
    await screen.findByRole("tablist");

    await user.click(screen.getByRole("tab", { name: /world & setting/i }));
    await user.type(screen.getByLabelText(/^outline/i), "My own outline");
    await user.type(screen.getByLabelText(/idea or guiding question/i), "a lighthouse mystery");
    await user.click(screen.getByRole("button", { name: /^suggest$/i }));

    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.getByLabelText(/^outline/i)).toHaveValue("My own outline");
  });
});
