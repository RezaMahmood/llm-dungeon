import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import ConversationPanel from "../../../src/components/Admin/StoryWizard/ConversationPanel.jsx";

describe("ConversationPanel", () => {
  it("renders the conversation history", () => {
    render(
      <ConversationPanel
        exchanges={[
          { role: "administrator", message: "A half-abandoned lighthouse...", timestamp: "2026-08-29T20:00:00Z" },
          { role: "system", message: "Who is the player in this story?", timestamp: "2026-08-29T20:00:01Z" },
        ]}
        onSendMessage={vi.fn()}
      />,
    );

    expect(screen.getByText(/A half-abandoned lighthouse/)).toBeInTheDocument();
    expect(screen.getByText(/Who is the player in this story/)).toBeInTheDocument();
  });

  it("sends a plain-language message and clears the input", async () => {
    const onSendMessage = vi.fn().mockResolvedValue(undefined);
    render(<ConversationPanel exchanges={[]} onSendMessage={onSendMessage} />);

    const input = screen.getByPlaceholderText(/describe your idea/i);
    await userEvent.type(input, "Make it 1908.");
    await userEvent.click(screen.getByRole("button", { name: /send/i }));

    expect(onSendMessage).toHaveBeenCalledWith("Make it 1908.");
    expect(input).toHaveValue("");
  });

  it("surfaces an error and keeps the message when sending fails", async () => {
    const onSendMessage = vi.fn().mockRejectedValue(new Error("network error"));
    render(<ConversationPanel exchanges={[]} onSendMessage={onSendMessage} />);

    const input = screen.getByPlaceholderText(/describe your idea/i);
    await userEvent.type(input, "Make it 1908.");
    await userEvent.click(screen.getByRole("button", { name: /send/i }));

    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(input).toHaveValue("Make it 1908.");
  });
});
