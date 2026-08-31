import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

const acquireTokenSilent = vi.fn();
const createDraft = vi.fn();
const getDraft = vi.fn();
const patchDraft = vi.fn();
const postMessage = vi.fn();

const mockInstance = { acquireTokenSilent, logoutRedirect: vi.fn() };
const mockAccounts = [{ homeAccountId: "home-1", username: "admin@example.com", name: "Ada B." }];

vi.mock("@azure/msal-react", () => ({
  useMsal: () => ({ instance: mockInstance, accounts: mockAccounts }),
}));

vi.mock("../../src/services/storyDraftService.js", () => ({
  createDraft: (...args) => createDraft(...args),
  getDraft: (...args) => getDraft(...args),
  patchDraft: (...args) => patchDraft(...args),
  postMessage: (...args) => postMessage(...args),
}));

import AdminStoryWizardPage from "../../src/pages/AdminStoryWizardPage.jsx";

const draftWith = (overrides = {}) => ({
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
  ...overrides,
});

const renderWizard = () =>
  render(
    <MemoryRouter initialEntries={["/admin/stories/new"]}>
      <AdminStoryWizardPage />
    </MemoryRouter>,
  );

describe("Wizard progress survives leaving via the nav bar (FR-005, SC-003)", () => {
  beforeEach(() => {
    sessionStorage.clear();
    acquireTokenSilent.mockReset().mockResolvedValue({ accessToken: "tok" });
    createDraft.mockReset();
    getDraft.mockReset();
    patchDraft.mockReset();
    postMessage.mockReset();
  });

  it("resumes the same draft — not a new blank one — when the wizard is revisited", async () => {
    const user = userEvent.setup();
    createDraft.mockResolvedValue({ draft: draftWith() });
    patchDraft.mockImplementation(async (_token, _id, updates) => ({
      status: "success",
      draft: draftWith(updates),
    }));

    // First visit: start a draft and save a name on step 1.
    const first = renderWizard();
    await screen.findByRole("tablist");

    await user.type(screen.getByLabelText(/^story name$/i), "The Lighthouse");
    await user.click(screen.getByRole("button", { name: /^save$/i }));

    await waitFor(() => expect(patchDraft).toHaveBeenCalled());
    expect(createDraft).toHaveBeenCalledTimes(1);

    // Leaving the wizard through a nav-bar link unmounts the page.
    first.unmount();

    // Returning must reopen the draft that was already saved, not start over.
    getDraft.mockResolvedValue({ draft: draftWith({ name: "The Lighthouse" }) });
    renderWizard();
    await screen.findByRole("tablist");

    await waitFor(() => expect(getDraft).toHaveBeenCalledWith("tok", "draft-1"));
    expect(createDraft).toHaveBeenCalledTimes(1); // no second blank draft
    expect(screen.getByLabelText(/name/i)).toHaveValue("The Lighthouse");
  });

  it("starts a fresh draft when there is nothing in progress to resume", async () => {
    createDraft.mockResolvedValue({ draft: draftWith() });

    renderWizard();
    await screen.findByRole("tablist");

    expect(getDraft).not.toHaveBeenCalled();
    expect(createDraft).toHaveBeenCalledTimes(1);
  });

  it("falls back to a new draft if the remembered one is gone", async () => {
    sessionStorage.setItem("llmdungeon.storyWizard.activeDraftId", "draft-stale");
    getDraft.mockRejectedValue(Object.assign(new Error("not found"), { response: { status: 404 } }));
    createDraft.mockResolvedValue({ draft: draftWith({ id: "draft-2" }) });

    renderWizard();
    await screen.findByRole("tablist");

    await waitFor(() => expect(createDraft).toHaveBeenCalledTimes(1));
    expect(sessionStorage.getItem("llmdungeon.storyWizard.activeDraftId")).toBe("draft-2");
  });
});
