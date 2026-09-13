import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import SessionsTable from "../../src/components/Admin/SessionsTable.jsx";

const session = (overrides = {}) => ({
  sessionId: "d668d9f8-9e26-4161-a95c-8500e8333219",
  sessionType: "player",
  storyId: "9f2a",
  storyName: "The Salt Mines",
  totalTokens: 16393,
  email: "player@company.internal",
  ...overrides,
});

const renderTable = (sessions, onSelectDelete = vi.fn()) => {
  render(<SessionsTable sessions={sessions} onSelectDelete={onSelectDelete} />);
  return onSelectDelete;
};

describe("SessionsTable (08-admin-sessions-spec.md §5)", () => {
  it("uses a real table with real column headers, in the design's order", () => {
    renderTable([session()]);

    const headers = screen.getAllByRole("columnheader").map((th) => th.textContent);
    expect(headers).toEqual(["Story", "Session ID", "Total tokens", "Account", ""]);
  });

  it("renders the deleted-story label as text, never as an empty cell or colour alone", () => {
    renderTable([session({ storyName: "(deleted story)" })]);

    const label = screen.getByText("(deleted story)");
    // Carried by a class whose meaning is also in the text itself — a screen reader and a
    // colour-blind viewer both get it (constitution Accessibility).
    expect(label).toHaveClass("sessions-deleted-story");
  });

  it("thousands-separates and right-aligns token totals so a column can be compared", () => {
    renderTable([session({ totalTokens: 16393 })]);

    const cell = screen.getByText("16,393");
    expect(cell).toHaveClass("sessions-tokens-cell");
  });

  it("renders zero as 0, not a dash or a blank", () => {
    renderTable([session({ totalTokens: 0 })]);

    expect(screen.getByText("0")).toBeInTheDocument();
  });

  it("renders the full session identifier in the wrapping monospace cell", () => {
    const fullId = "d668d9f8-9e26-4161-a95c-8500e8333219";
    renderTable([session({ sessionId: fullId })]);

    const cell = screen.getByText(fullId);
    expect(cell).toHaveClass("sessions-id-cell");
  });

  it("lets long account addresses wrap rather than widen the table", () => {
    renderTable([session({ email: "a-very-long-account-address@company.internal" })]);

    expect(screen.getByText("a-very-long-account-address@company.internal")).toHaveClass(
      "sessions-account-cell",
    );
  });

  it("hands the whole session to the delete handler, so the dialog can name it", async () => {
    const target = session();
    const onSelectDelete = renderTable([target]);

    await userEvent.click(screen.getByRole("button", { name: `Delete session ${target.sessionId}` }));

    expect(onSelectDelete).toHaveBeenCalledWith(target);
  });

  it("gives each row's delete a name that distinguishes it from the other rows", () => {
    renderTable([session({ sessionId: "aaa" }), session({ sessionId: "bbb" })]);

    // A column of identical "Delete" buttons would be unusable by screen reader.
    expect(screen.getByRole("button", { name: "Delete session aaa" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Delete session bbb" })).toBeInTheDocument();
  });

  it("uses a ghost button, not a permanently red one — the dialog carries the intent", () => {
    renderTable([session({ sessionId: "aaa" })]);

    // 08-admin-sessions-spec.md §7: accent stays reserved.
    expect(screen.getByRole("button", { name: "Delete session aaa" })).toHaveClass("btn-ghost");
  });
  it("greys out and spins only the row whose delete is in flight (issue #347)", async () => {
    const onSelectDelete = vi.fn();
    const { container } = render(
      <SessionsTable
        sessions={[session({ sessionId: "aaa" }), session({ sessionId: "bbb" })]}
        onSelectDelete={onSelectDelete}
        deletingSessionId="aaa"
      />,
    );

    const pendingRow = screen.getByRole("button", { name: "Delete session aaa" });
    expect(pendingRow).toBeDisabled();
    expect(pendingRow).toHaveAttribute("aria-busy", "true");
    expect(container.querySelectorAll(".spinner")).toHaveLength(1);

    // The other rows stay actionable — one delete in flight does not freeze the table.
    const otherRow = screen.getByRole("button", { name: "Delete session bbb" });
    expect(otherRow).toBeEnabled();
    await userEvent.click(otherRow);
    expect(onSelectDelete).toHaveBeenCalledTimes(1);
  });
});
