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

const listSessions = vi.fn();
vi.mock("../../src/services/sessionService.js", () => ({
  listSessions: (...args) => listSessions(...args),
  deleteSession: vi.fn(),
}));

import AuthenticatedLayout from "../../src/components/Layout/AuthenticatedLayout.jsx";
import AdminSessionsPage from "../../src/pages/AdminSessionsPage.jsx";

const session = (sessionId, storyName = "The Salt Mines") => ({
  sessionId,
  sessionType: "player",
  storyId: "9f2a",
  storyName,
  totalTokens: 100,
  email: "player@example.com",
});

describe("Admin Sessions refresh (031 FR-016; 019-spa-refresh-button)", () => {
  beforeEach(() => {
    listSessions.mockReset();
    mockUseCapabilities.mockReturnValue({
      hasPlayer: false,
      hasAdministrator: true,
      loading: false,
      error: null,
      denied: false,
      refetch: vi.fn(),
    });
  });

  const renderPage = () =>
    render(
      <MemoryRouter initialEntries={["/admin/sessions"]}>
        <AuthenticatedLayout>
          <AdminSessionsPage />
        </AuthenticatedLayout>
      </MemoryRouter>,
    );

  it("re-reads the list and recomputes the heading, without leaving the screen", async () => {
    listSessions
      .mockResolvedValueOnce({ sessions: [session("one")] })
      .mockResolvedValueOnce({ sessions: [session("one"), session("two", "Basement of Rats")] });

    renderPage();

    expect(await screen.findByRole("heading", { name: "1 session across 1 story" })).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /^refresh$/i }));

    expect(await screen.findByText("two")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "2 sessions across 2 stories" })).toBeInTheDocument();
    expect(listSessions).toHaveBeenCalledTimes(2);
  });

  it("keeps the previously loaded table visible behind a notice when a refresh fails", async () => {
    listSessions
      .mockResolvedValueOnce({ sessions: [session("one")] })
      .mockRejectedValueOnce(new Error("network down"));

    renderPage();

    expect(await screen.findByText("one")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /^refresh$/i }));

    // FR-016: never silently replaced with an empty list.
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.getByText("one")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "1 session across 1 story" })).toBeInTheDocument();
  });
});
