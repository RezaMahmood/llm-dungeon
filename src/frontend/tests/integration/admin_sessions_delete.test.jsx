import { render, screen, waitForElementToBeRemoved } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

const acquireTokenSilent = vi.fn();
const listSessions = vi.fn();
const deleteSession = vi.fn();

const mockInstance = { acquireTokenSilent, logoutRedirect: vi.fn() };
const mockAccounts = [{ homeAccountId: "home-1", username: "admin@example.com", name: "Ada B." }];

vi.mock("@azure/msal-react", () => ({
  useMsal: () => ({ instance: mockInstance, accounts: mockAccounts }),
}));

vi.mock("../../src/services/sessionService.js", () => ({
  listSessions: (...args) => listSessions(...args),
  deleteSession: (...args) => deleteSession(...args),
}));

import AdminSessionsPage from "../../src/pages/AdminSessionsPage.jsx";

const renderPage = () =>
  render(
    <MemoryRouter initialEntries={["/admin/sessions"]}>
      <AdminSessionsPage />
    </MemoryRouter>,
  );

const waitForLoad = () => waitForElementToBeRemoved(() => screen.queryByText(/loading sessions/i));

// Synthetic addresses only — a real one must never reach a fixture (Principle X).
const SESSIONS = [
  {
    sessionId: "d668d9f8-9e26-4161-a95c-8500e8333219",
    sessionType: "player",
    storyId: "9f2a",
    storyName: "The Salt Mines",
    totalTokens: 16393,
    email: "player@company.internal",
  },
  {
    sessionId: "5e871cbe-b979-41f9-b7a8-dd114243f8fa",
    sessionType: "test",
    storyId: "9f2a",
    storyName: "The Salt Mines",
    totalTokens: 0,
    email: "admin@company.internal",
  },
];

const FIRST = SESSIONS[0];

const openDialogForFirst = async (user) => {
  await user.click(screen.getByRole("button", { name: `Delete session ${FIRST.sessionId}` }));
  return screen.getByRole("dialog");
};

describe("Admin Sessions page — deleting a session (031 FR-006/FR-007/FR-014/FR-015)", () => {
  beforeEach(() => {
    acquireTokenSilent.mockReset().mockResolvedValue({ accessToken: "tok" });
    listSessions.mockReset().mockResolvedValue({ sessions: SESSIONS });
    deleteSession.mockReset();
  });

  it("asks for confirmation, naming the session, and deletes nothing yet", async () => {
    const user = userEvent.setup();
    renderPage();
    await waitForLoad();

    const dialog = await openDialogForFirst(user);

    expect(dialog).toHaveTextContent("Delete this session?");
    // The first 8 characters and the account, so the admin can check the row before
    // committing (08-admin-sessions-spec.md §6).
    expect(dialog).toHaveTextContent("d668d9f8…");
    expect(dialog).toHaveTextContent("player@company.internal");
    expect(dialog).toHaveTextContent(/cannot be undone/i);
    expect(deleteSession).not.toHaveBeenCalled();
  });

  it("keeps the session when the administrator backs out", async () => {
    const user = userEvent.setup();
    renderPage();
    await waitForLoad();

    await openDialogForFirst(user);
    await user.click(screen.getByRole("button", { name: "Keep it" }));

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(deleteSession).not.toHaveBeenCalled();
    expect(screen.getByText(FIRST.sessionId)).toBeInTheDocument();
  });

  it("removes the row and recomputes the heading once the server confirms", async () => {
    deleteSession.mockResolvedValue({ status: "deleted" });
    const user = userEvent.setup();
    renderPage();
    await waitForLoad();

    expect(screen.getByRole("heading", { name: "2 sessions across 1 story" })).toBeInTheDocument();

    await openDialogForFirst(user);
    await user.click(screen.getByRole("button", { name: "Delete session" }));

    expect(deleteSession).toHaveBeenCalledWith("tok", FIRST.sessionId);
    expect(await screen.findByRole("heading", { name: "1 session across 1 story" })).toBeInTheDocument();
    expect(screen.queryByText(FIRST.sessionId)).not.toBeInTheDocument();
  });

  it("deletes an administrator test-play session on the same terms", async () => {
    deleteSession.mockResolvedValue({ status: "deleted" });
    const user = userEvent.setup();
    renderPage();
    await waitForLoad();

    const testSession = SESSIONS[1];
    await user.click(screen.getByRole("button", { name: `Delete session ${testSession.sessionId}` }));
    await user.click(screen.getByRole("button", { name: "Delete session" }));

    expect(deleteSession).toHaveBeenCalledWith("tok", testSession.sessionId);
    expect(screen.queryByText(testSession.sessionId)).not.toBeInTheDocument();
    // The player session beside it is untouched.
    expect(screen.getByText(FIRST.sessionId)).toBeInTheDocument();
  });

  it("keeps the row and explains when the delete fails", async () => {
    deleteSession.mockRejectedValue({ response: { status: 500 } });
    const user = userEvent.setup();
    renderPage();
    await waitForLoad();

    await openDialogForFirst(user);
    await user.click(screen.getByRole("button", { name: "Delete session" }));

    // FR-014: never removed on the strength of a request that failed.
    expect(await screen.findByRole("alert")).toHaveTextContent(/still here/i);
    expect(screen.getByText(FIRST.sessionId)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "2 sessions across 1 story" })).toBeInTheDocument();
  });

  it("removes the row and says so when the session had already been deleted", async () => {
    deleteSession.mockRejectedValue({ response: { status: 404 } });
    const user = userEvent.setup();
    renderPage();
    await waitForLoad();

    await openDialogForFirst(user);
    await user.click(screen.getByRole("button", { name: "Delete session" }));

    // FR-015: a 404 is still the server confirming it is gone, so the table agrees with
    // the server rather than showing a row that no longer exists.
    expect(await screen.findByRole("alert")).toHaveTextContent(/already been removed/i);
    expect(screen.queryByText(FIRST.sessionId)).not.toBeInTheDocument();
  });
});
