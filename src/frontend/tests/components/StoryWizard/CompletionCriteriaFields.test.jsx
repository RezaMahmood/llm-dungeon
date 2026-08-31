import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import CompletionCriteriaFields from "../../../src/components/Admin/StoryWizard/CompletionCriteriaFields.jsx";

describe("CompletionCriteriaFields", () => {
  it("commits a single success condition without showing the any/all selector", async () => {
    const onChange = vi.fn();
    render(<CompletionCriteriaFields completionCriteria={null} onChange={onChange} />);

    await userEvent.click(screen.getByRole("button", { name: /add success condition/i }));
    await userEvent.type(screen.getByLabelText(/success condition/i), "Find the keeper");
    await userEvent.tab();

    expect(onChange).toHaveBeenCalledWith({
      maxDurationMinutes: null,
      successConditions: ["Find the keeper"],
      failureConditions: [],
      rule: null,
    });
    expect(screen.queryByText(/how should multiple conditions combine/i)).not.toBeInTheDocument();
  });

  it("shows the any/all rule selector once more than one condition is defined", () => {
    render(
      <CompletionCriteriaFields
        completionCriteria={{
          maxDurationMinutes: 20,
          successConditions: ["Find the keeper"],
          failureConditions: ["Leave the cove"],
          rule: "any",
        }}
        onChange={vi.fn()}
      />,
    );

    expect(screen.getByText(/how should multiple conditions combine/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^any$/i)).toBeChecked();
  });

  it("defaults rule to any when a second condition is committed without picking one (regression)", async () => {
    // The backend rejects completionCriteria with >1 condition and no rule (data-model.md).
    // Previously, adding a failure condition right after an existing success condition and
    // blurring it committed rule: null, which the server 422'd — silently, since nothing
    // awaited/caught the write. This locks in that the component itself never produces
    // that invalid combination.
    const onChange = vi.fn();
    render(
      <CompletionCriteriaFields
        completionCriteria={{ maxDurationMinutes: null, successConditions: ["Find the keeper"], failureConditions: [], rule: null }}
        onChange={onChange}
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: /add failure condition/i }));
    await userEvent.type(screen.getByLabelText(/failure condition/i), "Leave the cove");
    await userEvent.tab();

    expect(onChange).toHaveBeenCalledWith({
      maxDurationMinutes: null,
      successConditions: ["Find the keeper"],
      failureConditions: ["Leave the cove"],
      rule: "any",
    });
  });

  it("keeps a just-added, uncommitted condition row when the parent re-renders with unrelated but content-identical completionCriteria (regression)", async () => {
    // Same root cause as CharacterTypeList's equivalent test: the wizard replaces the
    // whole draft object on every write, handing down a fresh completionCriteria object
    // reference even when its content is unchanged. Resetting local state on prop
    // *reference* alone wiped an in-progress "Add success condition" row.
    const onChange = vi.fn();
    const initial = { maxDurationMinutes: null, successConditions: [], failureConditions: [], rule: null };
    const { rerender } = render(<CompletionCriteriaFields completionCriteria={initial} onChange={onChange} />);

    await userEvent.click(screen.getByRole("button", { name: /add success condition/i }));
    expect(screen.getByLabelText(/success condition/i)).toBeInTheDocument();

    // A new object instance, same content — simulates an unrelated draft refresh.
    rerender(<CompletionCriteriaFields completionCriteria={{ ...initial }} onChange={onChange} />);

    expect(screen.getByLabelText(/success condition/i)).toBeInTheDocument();
  });

  it("clears the whole structure when the last success condition is removed", async () => {
    const onChange = vi.fn();
    render(
      <CompletionCriteriaFields
        completionCriteria={{ maxDurationMinutes: null, successConditions: ["Find the keeper"], failureConditions: [], rule: null }}
        onChange={onChange}
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: /remove/i }));

    expect(onChange).toHaveBeenCalledWith(null);
  });
});
