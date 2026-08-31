import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const acquireTokenSilent = vi.fn().mockResolvedValue({ accessToken: "tok" });
const mockInstance = { acquireTokenSilent };
const mockAccounts = [{ homeAccountId: "home-1", username: "admin@example.com" }];

vi.mock("@azure/msal-react", () => ({
  useMsal: () => ({ instance: mockInstance, accounts: mockAccounts }),
}));

const createDraft = vi.fn();
const getDraft = vi.fn();
const patchDraft = vi.fn();
const postMessage = vi.fn();
vi.mock("../../src/services/storyDraftService.js", () => ({
  createDraft: (...args) => createDraft(...args),
  getDraft: (...args) => getDraft(...args),
  patchDraft: (...args) => patchDraft(...args),
  postMessage: (...args) => postMessage(...args),
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

describe("Admin Story Wizard unsaved-changes warning (FR-010)", () => {
  let addSpy;

  beforeEach(() => {
    createDraft.mockReset();
    getDraft.mockReset();
    patchDraft.mockReset();
    postMessage.mockReset();
    sessionStorage.clear();
    addSpy = vi.spyOn(window, "addEventListener");
  });

  afterEach(() => {
    addSpy.mockRestore();
  });

  it("arms the warning as soon as a field is dirtied, before Save is even clicked", async () => {
    createDraft.mockResolvedValueOnce({ draft: EMPTY_DRAFT });

    render(
      <MemoryRouter initialEntries={["/admin/stories/new"]}>
        <AdminStoryWizardPage />
      </MemoryRouter>,
    );

    expect(await screen.findByRole("tablist")).toBeInTheDocument();
    expect(addSpy).not.toHaveBeenCalledWith("beforeunload", expect.any(Function));

    await userEvent.type(screen.getByLabelText(/story name/i), "A Name");

    expect(addSpy).toHaveBeenCalledWith("beforeunload", expect.any(Function));
  });

  it("disarms the warning once the save succeeds", async () => {
    createDraft.mockResolvedValueOnce({ draft: EMPTY_DRAFT });
    patchDraft.mockResolvedValueOnce({
      status: "success",
      draft: { ...EMPTY_DRAFT, name: "A Name" },
    });

    render(
      <MemoryRouter initialEntries={["/admin/stories/new"]}>
        <AdminStoryWizardPage />
      </MemoryRouter>,
    );

    expect(await screen.findByRole("tablist")).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText(/story name/i), "A Name");
    await userEvent.click(screen.getByRole("button", { name: /^save$/i }));

    const removeSpy = vi.spyOn(window, "removeEventListener");
    await screen.findByText(/saved/i);
    expect(removeSpy).toHaveBeenCalledWith("beforeunload", expect.any(Function));
    removeSpy.mockRestore();
  });
});
