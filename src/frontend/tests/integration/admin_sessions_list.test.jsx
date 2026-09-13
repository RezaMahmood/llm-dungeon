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
  deleteSession: vi.fn(),
}));

import AdminSessionsPage from "../../src/pages/AdminSessionsPage.jsx";

const renderPage = () =>
  render(
    <MemoryRouter initialEntries={["/admin/sessions"]}>
      <AdminSessionsPage />
    </MemoryRouter>,
  );

const waitForLoad = () => waitForElementToBeRemoved(() => screen.queryByText(/loading sessions/i));

const session = (overrides = {}) => ({
  sessionId: "b7e1",
  sessionType: "player",
  storyId: "9f2a",
  storyName: "The Salt Mines",
  totalTokens: 100,
  email: "player@example.com",
  ...overrides,
});

describe("Admin Sessions page — the list (026-token-usage FR-015/FR-018, 031 FR-002–FR-005)", () => {
  beforeEach(() => {
    acquireTokenSilent.mockReset().mockResolvedValue({ accessToken: "tok" });
    listSessions.mockReset();
  });

  it("lists a real player session and an admin test-play session with story, id, tokens, and account", async () => {
    listSessions.mockResolvedValue({
      sessions: [
        session({ sessionId: "b7e1", totalTokens: 6420 }),
        session({ sessionId: "c3d9", sessionType: "test", totalTokens: 1180, email: "admin@example.com" }),
      ],
    });

    renderPage();
    await waitForLoad();

    expect(screen.getByRole("columnheader", { name: "Story" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Session ID" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Total tokens" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Account" })).toBeInTheDocument();

    const playerRow = screen.getByText("b7e1").closest("tr");
    expect(playerRow).toHaveTextContent("The Salt Mines");
    expect(playerRow).toHaveTextContent("6,420");
    expect(playerRow).toHaveTextContent("player@example.com");

    const testRow = screen.getByText("c3d9").closest("tr");
    expect(testRow).toHaveTextContent("1,180");
    expect(testRow).toHaveTextContent("admin@example.com");
  });

  it("renders the full session identifier rather than truncating it", async () => {
    const fullId = "d668d9f8-9e26-4161-a95c-8500e8333219";
    listSessions.mockResolvedValue({ sessions: [session({ sessionId: fullId })] });

    renderPage();
    await waitForLoad();

    expect(screen.getByText(fullId)).toBeInTheDocument();
  });

  it("shows the deleted-story fallback for a session whose story no longer exists", async () => {
    listSessions.mockResolvedValue({ sessions: [session({ storyName: "(deleted story)" })] });

    renderPage();
    await waitForLoad();

    expect(screen.getByText("(deleted story)")).toBeInTheDocument();
  });

  it("shows the unprovisioned-account fallback when no account matches the session", async () => {
    listSessions.mockResolvedValue({ sessions: [session({ email: "(no longer provisioned)" })] });

    renderPage();
    await waitForLoad();

    expect(screen.getByText("(no longer provisioned)")).toBeInTheDocument();
  });

  it("renders zero, not a blank cell, for a session with no recorded turns yet", async () => {
    listSessions.mockResolvedValue({ sessions: [session({ totalTokens: 0 })] });

    renderPage();
    await waitForLoad();

    expect(screen.getByText("b7e1").closest("tr")).toHaveTextContent("0");
  });

  it("offers a delete action per row, naming the session so rows are distinguishable", async () => {
    listSessions.mockResolvedValue({
      sessions: [session({ sessionId: "b7e1" }), session({ sessionId: "c3d9" })],
    });

    renderPage();
    await waitForLoad();

    // Supersedes 026-token-usage FR-016's read-only rule (031 FR-006).
    expect(screen.getByRole("button", { name: "Delete session b7e1" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Delete session c3d9" })).toBeInTheDocument();
  });
});

describe("Admin Sessions page — the heading (031 FR-002)", () => {
  beforeEach(() => {
    acquireTokenSilent.mockReset().mockResolvedValue({ accessToken: "tok" });
    listSessions.mockReset();
  });

  it("counts sessions and the distinct stories they belong to", async () => {
    listSessions.mockResolvedValue({
      sessions: [
        session({ sessionId: "a", storyName: "The Salt Mines" }),
        session({ sessionId: "b", storyName: "The Salt Mines" }),
        session({ sessionId: "c", storyName: "Basement of Rats" }),
      ],
    });

    renderPage();
    await waitForLoad();

    // Two sessions of one story count that story once.
    expect(screen.getByRole("heading", { name: "3 sessions across 2 stories" })).toBeInTheDocument();
  });

  it("singularises each half of the heading independently", async () => {
    listSessions.mockResolvedValue({ sessions: [session()] });

    renderPage();
    await waitForLoad();

    expect(screen.getByRole("heading", { name: "1 session across 1 story" })).toBeInTheDocument();
  });

  it("does not count deleted stories, even several distinct ones", async () => {
    listSessions.mockResolvedValue({
      sessions: [
        session({ sessionId: "a", storyName: "The Salt Mines" }),
        session({ sessionId: "b", storyName: "(deleted story)" }),
        session({ sessionId: "c", storyName: "(deleted story)" }),
      ],
    });

    renderPage();
    await waitForLoad();

    expect(screen.getByRole("heading", { name: "3 sessions across 1 story" })).toBeInTheDocument();
  });

  it("reads 'No sessions' and replaces the table with an explanation when the list is empty", async () => {
    listSessions.mockResolvedValue({ sessions: [] });

    renderPage();
    await waitForLoad();

    expect(screen.getByRole("heading", { name: "No sessions" })).toBeInTheDocument();
    expect(screen.getByText(/no sessions yet\. they appear here as soon as someone starts a story\./i)).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("never claims a count before the first load has succeeded", async () => {
    let resolve;
    listSessions.mockReturnValue(new Promise((r) => {
      resolve = r;
    }));

    renderPage();

    // Mid-load the heading must not read "No sessions" — that would be a claim about
    // data not yet seen.
    expect(screen.getByRole("heading", { name: "Sessions" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "No sessions" })).not.toBeInTheDocument();

    resolve({ sessions: [] });
    await waitForLoad();
  });
});
