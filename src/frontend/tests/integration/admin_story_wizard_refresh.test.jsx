import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

const acquireTokenSilent = vi.fn().mockResolvedValue({ accessToken: "tok" });
const mockInstance = { acquireTokenSilent, logoutRedirect: vi.fn() };
const mockAccounts = [{ homeAccountId: "home-1", username: "admin@example.com", name: "Admin A." }];

vi.mock("@azure/msal-react", () => ({
  useMsal: () => ({ instance: mockInstance, accounts: mockAccounts }),
}));

const mockUseCapabilities = vi.fn();
vi.mock("../../src/hooks/useCapabilities.js", () => ({
  useCapabilities: () => mockUseCapabilities(),
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

import AuthenticatedLayout from "../../src/components/Layout/AuthenticatedLayout.jsx";
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

describe("Admin Story Wizard refresh (FR-003, contracts/refresh-control.md)", () => {
  beforeEach(() => {
    createDraft.mockReset();
    getDraft.mockReset();
    patchDraft.mockReset();
    postMessage.mockReset();
    sessionStorage.clear();
    mockUseCapabilities.mockReturnValue({
      hasPlayer: false,
      hasAdministrator: true,
      loading: false,
      error: null,
      denied: false,
      refetch: vi.fn(),
    });
  });

  it("selecting the refresh control re-fetches the draft and leaves activeStep unchanged", async () => {
    createDraft.mockResolvedValueOnce({ draft: EMPTY_DRAFT });
    getDraft.mockResolvedValueOnce({
      draft: { ...EMPTY_DRAFT, name: "Refetched Name" },
    });

    render(
      <MemoryRouter initialEntries={["/admin/stories/new"]}>
        <AuthenticatedLayout>
          <AdminStoryWizardPage />
        </AuthenticatedLayout>
      </MemoryRouter>,
    );

    expect(await screen.findByRole("tablist")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("tab", { name: /world & setting/i }));
    expect(screen.getByRole("tab", { name: /world & setting/i })).toHaveAttribute(
      "aria-selected",
      "true",
    );

    await userEvent.click(screen.getByRole("button", { name: /^refresh$/i }));

    expect(getDraft).toHaveBeenCalledWith("tok", "draft-1");
    // Still on the World & setting step — a refresh must not reset activeStep.
    await screen.findByRole("tab", { name: /world & setting/i, selected: true });
  });
});
