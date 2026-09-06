import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import PauseDialog from "../../src/components/Play/PauseDialog.jsx";

describe("PauseDialog (008-core-gameplay, FR-016)", () => {
  it("renders where the game was saved", () => {
    render(<PauseDialog locationLabel="the keeper's stairs" onKeepPlaying={vi.fn()} onConfirmExit={vi.fn()} />);

    expect(screen.getByText(/your story is saved at the keeper's stairs/i)).toBeInTheDocument();
  });

  it("calls the confirm-exit callback", async () => {
    const onConfirmExit = vi.fn();
    const user = userEvent.setup();
    render(<PauseDialog locationLabel="the cove" onKeepPlaying={vi.fn()} onConfirmExit={onConfirmExit} />);

    await user.click(screen.getByRole("button", { name: /save and exit/i }));

    expect(onConfirmExit).toHaveBeenCalled();
  });

  it("calls the cancel callback, leaving the session untouched", async () => {
    const onKeepPlaying = vi.fn();
    const onConfirmExit = vi.fn();
    const user = userEvent.setup();
    render(<PauseDialog locationLabel="the cove" onKeepPlaying={onKeepPlaying} onConfirmExit={onConfirmExit} />);

    await user.click(screen.getByRole("button", { name: /keep playing/i }));

    expect(onKeepPlaying).toHaveBeenCalled();
    expect(onConfirmExit).not.toHaveBeenCalled();
  });
});
