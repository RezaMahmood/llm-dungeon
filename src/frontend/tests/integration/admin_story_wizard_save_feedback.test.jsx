import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

const acquireTokenSilent = vi.fn();
const createDraft = vi.fn();
const getDraft = vi.fn();
const patchDraft = vi.fn();
const suggestWorldPrompt = vi.fn();
const generateStory = vi.fn();

const mockInstance = { acquireTokenSilent };
const mockAccounts = [{ homeAccountId: "home-1", username: "admin@example.com" }];

vi.mock("@azure/msal-react", () => ({
  useMsal: () => ({ instance: mockInstance, accounts: mockAccounts }),
}));

vi.mock("../../src/services/storyDraftService.js", () => ({
  createDraft: (...args) => createDraft(...args),
  getDraft: (...args) => getDraft(...args),
  patchDraft: (...args) => patchDraft(...args),
  suggestWorldPrompt: (...args) => suggestWorldPrompt(...args),
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
  blurb: null,
  characterTypes: [],
  completionCriteria: null,
};

const unauthorized = () =>
  Object.assign(new Error("unauthorized"), {
    response: { status: 401, data: { error: "unauthorized", message: "Unauthorized" } },
  });

const renderWizard = () =>
  render(
    <MemoryRouter initialEntries={["/admin/stories/new"]}>
      <AdminStoryWizardPage />
    </MemoryRouter>,
  );

describe("Story wizard saves with a current token and confirms only real saves (#137)", () => {
  beforeEach(() => {
    sessionStorage.clear();
    acquireTokenSilent.mockReset().mockResolvedValue({ accessToken: "tok" });
    createDraft.mockReset().mockResolvedValue({ draft: EMPTY_DRAFT });
    getDraft.mockReset();
    patchDraft.mockReset();
    suggestWorldPrompt.mockReset();
    generateStory.mockReset();
  });

  it("sends a token acquired for this write, not the one the wizard opened with", async () => {
    // The wizard is a long-lived screen: the token it opened with can have expired by
    // the time the administrator gets round to saving a name.
    acquireTokenSilent
      .mockResolvedValueOnce({ accessToken: "tok-at-open" })
      .mockResolvedValue({ accessToken: "tok-now" });
    patchDraft.mockResolvedValue({ status: "success", draft: { ...EMPTY_DRAFT, name: "The Lighthouse" } });

    renderWizard();
    await screen.findByRole("tablist");

    await userEvent.type(screen.getByLabelText(/^story name$/i), "The Lighthouse");
    await userEvent.click(screen.getByRole("button", { name: /^save$/i }));

    await waitFor(() => expect(patchDraft).toHaveBeenCalled());
    expect(patchDraft).toHaveBeenCalledWith("tok-now", "draft-1", {
      name: "The Lighthouse",
      coverImageUrl: "",
      blurb: "",
    });
  });

  it("does not claim the name was saved when the server rejected the write", async () => {
    patchDraft.mockRejectedValue(unauthorized());

    renderWizard();
    await screen.findByRole("tablist");

    await userEvent.type(screen.getByLabelText(/^story name$/i), "The Lighthouse");
    await userEvent.click(screen.getByRole("button", { name: /^save$/i }));

    // The failure is told to the administrator, not only to the browser console — and
    // an expired sign-in is named as such rather than as a problem with the name typed.
    expect(await screen.findByRole("alert")).toHaveTextContent(/sign-in has expired/i);
    expect(screen.queryByText(/^saved$/i)).not.toBeInTheDocument();
  });

  it("confirms the save once the write actually lands", async () => {
    patchDraft.mockResolvedValue({ status: "success", draft: { ...EMPTY_DRAFT, name: "The Lighthouse" } });

    renderWizard();
    await screen.findByRole("tablist");

    await userEvent.type(screen.getByLabelText(/^story name$/i), "The Lighthouse");
    await userEvent.click(screen.getByRole("button", { name: /^save$/i }));

    expect(await screen.findByText(/^saved$/i)).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("clears a failed save's message as soon as the administrator edits again", async () => {
    patchDraft.mockRejectedValue(unauthorized());

    renderWizard();
    await screen.findByRole("tablist");

    await userEvent.type(screen.getByLabelText(/^story name$/i), "The Lighthouse");
    await userEvent.click(screen.getByRole("button", { name: /^save$/i }));
    await screen.findByRole("alert");

    await userEvent.type(screen.getByLabelText(/^story name$/i), "!");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
