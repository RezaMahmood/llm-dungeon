import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

const acquireTokenSilent = vi.fn();
const createDraft = vi.fn();
const getDraft = vi.fn();
const patchDraft = vi.fn();
const suggestWorldPrompt = vi.fn();

const mockInstance = { acquireTokenSilent, logoutRedirect: vi.fn() };
const mockAccounts = [{ homeAccountId: "home-1", username: "admin@example.com", name: "Ada B." }];

vi.mock("@azure/msal-react", () => ({
  useMsal: () => ({ instance: mockInstance, accounts: mockAccounts }),
}));

vi.mock("../../src/services/storyDraftService.js", () => ({
  createDraft: (...args) => createDraft(...args),
  getDraft: (...args) => getDraft(...args),
  patchDraft: (...args) => patchDraft(...args),
  suggestWorldPrompt: (...args) => suggestWorldPrompt(...args),
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
  ...overrides,
});

const KEY = "llmdungeon.storyWizard.activeDraftId";
const rememberDraft = (id, savedAt = Date.now()) => sessionStorage.setItem(KEY, JSON.stringify({ id, savedAt }));
const rememberedDraftId = () => JSON.parse(sessionStorage.getItem(KEY) ?? "null")?.id ?? null;

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
    suggestWorldPrompt.mockReset();
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
    rememberDraft("draft-stale");
    getDraft.mockRejectedValue(Object.assign(new Error("not found"), { response: { status: 404 } }));
    createDraft.mockResolvedValue({ draft: draftWith({ id: "draft-2" }) });

    renderWizard();
    await screen.findByRole("tablist");

    await waitFor(() => expect(createDraft).toHaveBeenCalledTimes(1));
    expect(rememberedDraftId()).toBe("draft-2");
  });

  // #135: the wizard logged a 404 on every load for a draft that could only be gone.
  // An expected "nothing to resume" state must cost no request at all.
  it("does not request a remembered draft that can only have expired", async () => {
    rememberDraft("draft-expired", Date.now() - 25 * 60 * 60 * 1000);
    createDraft.mockResolvedValue({ draft: draftWith({ id: "draft-3" }) });

    renderWizard();
    await screen.findByRole("tablist");

    expect(getDraft).not.toHaveBeenCalled();
    await waitFor(() => expect(rememberedDraftId()).toBe("draft-3"));
  });

  it("does not request a remembered draft left behind without a timestamp", async () => {
    sessionStorage.setItem(KEY, "draft-from-an-older-build");
    createDraft.mockResolvedValue({ draft: draftWith({ id: "draft-4" }) });

    renderWizard();
    await screen.findByRole("tablist");

    expect(getDraft).not.toHaveBeenCalled();
    await waitFor(() => expect(rememberedDraftId()).toBe("draft-4"));
  });

  it("keeps the remembered draft alive while it is still being written to", async () => {
    const user = userEvent.setup();
    // Stored 23h ago: within the TTL now, but past it by the time the admin comes back.
    const nearlyExpired = Date.now() - 23 * 60 * 60 * 1000;
    rememberDraft("draft-1", nearlyExpired);
    getDraft.mockResolvedValue({ draft: draftWith() });
    patchDraft.mockImplementation(async (_token, _id, updates) => ({
      status: "success",
      draft: draftWith(updates),
    }));

    renderWizard();
    await screen.findByRole("tablist");
    await waitFor(() => expect(getDraft).toHaveBeenCalledWith("tok", "draft-1"));

    await user.type(screen.getByLabelText(/^story name$/i), "The Lighthouse");
    await user.click(screen.getByRole("button", { name: /^save$/i }));

    // The write reset the draft's TTL server-side, so the remembered id must be
    // re-stamped rather than going on ageing out from when it was first stored.
    await waitFor(() => expect(patchDraft).toHaveBeenCalled());
    await waitFor(() =>
      expect(JSON.parse(sessionStorage.getItem(KEY)).savedAt).toBeGreaterThan(nearlyExpired),
    );
    expect(rememberedDraftId()).toBe("draft-1");
  });

  // A failure that says nothing about whether the draft still exists must not silently
  // start a second draft and strand the administrator's saved work.
  it("does not discard the remembered draft when the resume fails for another reason", async () => {
    rememberDraft("draft-1");
    getDraft.mockRejectedValue(Object.assign(new Error("unauthorized"), { response: { status: 401 } }));

    renderWizard();

    await screen.findByRole("alert");
    expect(createDraft).not.toHaveBeenCalled();
    expect(rememberedDraftId()).toBe("draft-1");
  });
});
