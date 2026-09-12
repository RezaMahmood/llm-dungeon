import { render, screen, waitForElementToBeRemoved } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

const acquireTokenSilent = vi.fn();
const listSessions = vi.fn();

// Stable references: a fresh `instance`/`accounts` object per render would
// re-create AdminSessionsPage's `refresh` callback every render and loop the effect.
const mockInstance = { acquireTokenSilent, logoutRedirect: vi.fn() };
const mockAccounts = [{ homeAccountId: "home-1", username: "admin@example.com", name: "Ada B." }];

vi.mock("@azure/msal-react", () => ({
  useMsal: () => ({ instance: mockInstance, accounts: mockAccounts }),
}));

vi.mock("../../src/services/sessionService.js", () => ({
  listSessions: (...args) => listSessions(...args),
}));

import AdminSessionsPage from "../../src/pages/AdminSessionsPage.jsx";

const renderPage = () =>
  render(
    <MemoryRouter initialEntries={["/admin/sessions"]}>
      <AdminSessionsPage />
    </MemoryRouter>,
  );

const waitForLoad = () => waitForElementToBeRemoved(() => screen.queryByText(/loading sessions/i));

describe("Admin Sessions page (026-token-usage FR-015, FR-016, FR-018)", () => {
  beforeEach(() => {
    acquireTokenSilent.mockReset().mockResolvedValue({ accessToken: "tok" });
    listSessions.mockReset();
  });

  it("lists a real player session and an admin test-play session with story, id, tokens, and email", async () => {
    listSessions.mockResolvedValue({
      sessions: [
        {
          sessionId: "b7e1",
          sessionType: "player",
          storyId: "9f2a",
          storyName: "The Salt Mines",
          totalTokens: 6420,
          email: "player@example.com",
        },
        {
          sessionId: "c3d9",
          sessionType: "test",
          storyId: "9f2a",
          storyName: "The Salt Mines",
          totalTokens: 1180,
          email: "admin@example.com",
        },
      ],
    });

    renderPage();
    await waitForLoad();

    expect(screen.getByRole("columnheader", { name: "Story" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Session ID" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Total Tokens" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Email" })).toBeInTheDocument();

    const playerRow = screen.getByText("b7e1").closest("tr");
    expect(playerRow).toHaveTextContent("The Salt Mines");
    expect(playerRow).toHaveTextContent("6,420");
    expect(playerRow).toHaveTextContent("player@example.com");

    const testRow = screen.getByText("c3d9").closest("tr");
    expect(testRow).toHaveTextContent("The Salt Mines");
    expect(testRow).toHaveTextContent("1,180");
    expect(testRow).toHaveTextContent("admin@example.com");
  });

  it("shows the deleted-story fallback for a session whose story no longer exists", async () => {
    listSessions.mockResolvedValue({
      sessions: [
        {
          sessionId: "b7e1",
          sessionType: "player",
          storyId: "missing",
          storyName: "(deleted story)",
          totalTokens: 100,
          email: "player@example.com",
        },
      ],
    });

    renderPage();
    await waitForLoad();

    expect(screen.getByText("(deleted story)")).toBeInTheDocument();
  });

  it("shows the unprovisioned-account fallback when no account matches the session", async () => {
    listSessions.mockResolvedValue({
      sessions: [
        {
          sessionId: "b7e1",
          sessionType: "player",
          storyId: "9f2a",
          storyName: "The Salt Mines",
          totalTokens: 100,
          email: "(no longer provisioned)",
        },
      ],
    });

    renderPage();
    await waitForLoad();

    expect(screen.getByText("(no longer provisioned)")).toBeInTheDocument();
  });

  it("renders zero, not a blank cell, for a session with no recorded turns yet", async () => {
    listSessions.mockResolvedValue({
      sessions: [
        {
          sessionId: "b7e1",
          sessionType: "player",
          storyId: "9f2a",
          storyName: "The Salt Mines",
          totalTokens: 0,
          email: "player@example.com",
        },
      ],
    });

    renderPage();
    await waitForLoad();

    expect(screen.getByText("b7e1").closest("tr")).toHaveTextContent("0");
  });

  it("shows an empty state, not an error, when no sessions exist yet", async () => {
    listSessions.mockResolvedValue({ sessions: [] });

    renderPage();
    await waitForLoad();

    expect(screen.getByText(/no gameplay sessions yet/i)).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("is read-only: no edit, delete, or other action control appears anywhere on the page", async () => {
    listSessions.mockResolvedValue({
      sessions: [
        {
          sessionId: "b7e1",
          sessionType: "player",
          storyId: "9f2a",
          storyName: "The Salt Mines",
          totalTokens: 100,
          email: "player@example.com",
        },
      ],
    });

    renderPage();
    await waitForLoad();

    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });
});
