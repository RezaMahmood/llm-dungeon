import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const deleteSession = vi.fn();
vi.mock("../../../src/services/gameService.js", () => ({
  deleteSession: (...args) => deleteSession(...args),
}));

import SessionDeleteAction from "../../../src/components/Home/SessionDeleteAction.jsx";

const SESSION = { sessionId: "session-1", adventureName: "The Lighthouse at Gullwing Cove" };

describe("SessionDeleteAction (028-home-page-redesign FR-008)", () => {
  beforeEach(() => {
    deleteSession.mockReset();
  });

  it("shows the canonical confirmation copy naming the story, not a browser confirm()", async () => {
    const user = userEvent.setup();
    render(<SessionDeleteAction session={SESSION} token="tok" onDeleted={vi.fn()} />);

    await user.click(screen.getByRole("button", { name: /delete this session/i }));

    const dialog = await screen.findByRole("dialog");
    expect(dialog).toHaveTextContent('Delete your saved session for “The Lighthouse at Gullwing Cove”?');
    expect(dialog).toHaveTextContent(/your progress will be lost/i);
  });

  it("cancel leaves the session untouched", async () => {
    const onDeleted = vi.fn();
    const user = userEvent.setup();
    render(<SessionDeleteAction session={SESSION} token="tok" onDeleted={onDeleted} />);

    await user.click(screen.getByRole("button", { name: /delete this session/i }));
    await user.click(await screen.findByRole("button", { name: /^cancel$/i }));

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(deleteSession).not.toHaveBeenCalled();
    expect(onDeleted).not.toHaveBeenCalled();
  });

  it("confirm deletes the session and reports it via onDeleted", async () => {
    deleteSession.mockResolvedValue({ status: "deleted", sessionId: "session-1" });
    const onDeleted = vi.fn();
    const user = userEvent.setup();
    render(<SessionDeleteAction session={SESSION} token="tok" onDeleted={onDeleted} />);

    await user.click(screen.getByRole("button", { name: /delete this session/i }));
    await user.click(await screen.findByRole("button", { name: /^delete$/i }));

    expect(deleteSession).toHaveBeenCalledWith("tok", "session-1");
    expect(onDeleted).toHaveBeenCalledWith("session-1");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("a 404 (already gone) is treated as success, not an error", async () => {
    deleteSession.mockRejectedValue({ response: { status: 404 } });
    const onDeleted = vi.fn();
    const user = userEvent.setup();
    render(<SessionDeleteAction session={SESSION} token="tok" onDeleted={onDeleted} />);

    await user.click(screen.getByRole("button", { name: /delete this session/i }));
    await user.click(await screen.findByRole("button", { name: /^delete$/i }));

    expect(onDeleted).toHaveBeenCalledWith("session-1");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("a genuine failure keeps the session and shows an error", async () => {
    deleteSession.mockRejectedValue(new Error("network error"));
    const onDeleted = vi.fn();
    const user = userEvent.setup();
    render(<SessionDeleteAction session={SESSION} token="tok" onDeleted={onDeleted} />);

    await user.click(screen.getByRole("button", { name: /delete this session/i }));
    await user.click(await screen.findByRole("button", { name: /^delete$/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/could not delete this session/i);
    expect(onDeleted).not.toHaveBeenCalled();
  });

  it("the trigger stops propagation so it never fires an ancestor link", async () => {
    const onCardClick = vi.fn();
    const user = userEvent.setup();
    render(
      // eslint-disable-next-line jsx-a11y/click-events-have-key-events, jsx-a11y/no-static-element-interactions
      <div onClick={onCardClick}>
        <SessionDeleteAction session={SESSION} token="tok" onDeleted={vi.fn()} />
      </div>,
    );

    await user.click(screen.getByRole("button", { name: /delete this session/i }));

    expect(onCardClick).not.toHaveBeenCalled();
  });
});
