import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const importStoryConfiguration = vi.fn();

vi.mock("../../src/services/storyDraftService.js", () => ({
  importStoryConfiguration: (...args) => importStoryConfiguration(...args),
}));

import StoryConfigUpload from "../../src/components/Admin/StoryConfigUpload.jsx";

function jsonFile(content, name = "story.json") {
  return new File([content], name, { type: "application/json" });
}

const VALID_OVERWRITE = {
  id: "story-1",
  name: "The Sunken Library",
  worldPrompt: "A flooded library.",
  characterTypes: [{ name: "Archivist" }],
  completionCriteria: { successConditions: ["Recover the ledger"] },
};

const VALID_NEW = {
  worldPrompt: "A flooded library.",
  characterTypes: [{ name: "Archivist" }],
  completionCriteria: { successConditions: ["Recover the ledger"] },
};

async function upload(content, filename = "story.json") {
  const input = screen.getByLabelText(/upload configuration file/i);
  await userEvent.upload(input, jsonFile(content, filename));
}

describe("StoryConfigUpload (FR-005, contracts/api.md → Validation runs on both sides)", () => {
  beforeEach(() => {
    importStoryConfiguration.mockReset();
  });

  it("confirms the named overwrite target for an id-carrying file", async () => {
    render(<StoryConfigUpload token="tok" onImported={vi.fn()} />);

    await upload(JSON.stringify(VALID_OVERWRITE));

    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveTextContent("story-1");
    expect(importStoryConfiguration).not.toHaveBeenCalled();
  });

  it("prompts for a title for an id-less file", async () => {
    render(<StoryConfigUpload token="tok" onImported={vi.fn()} />);

    await upload(JSON.stringify(VALID_NEW));

    expect(screen.getByRole("dialog")).toHaveTextContent(/name this new story/i);
  });

  it("posts the confirmed overwrite with configurationText and confirmOverwriteStoryId", async () => {
    importStoryConfiguration.mockResolvedValueOnce({ status: "updated", storyId: "story-1", story: {} });
    render(<StoryConfigUpload token="tok" onImported={vi.fn()} />);
    const text = JSON.stringify(VALID_OVERWRITE);

    await upload(text);
    await userEvent.click(screen.getByRole("button", { name: /^overwrite$/i }));

    expect(importStoryConfiguration).toHaveBeenCalledWith("tok", {
      configurationText: text,
      confirmOverwriteStoryId: "story-1",
    });
  });

  it("posts the id-less upload with the supplied title", async () => {
    importStoryConfiguration.mockResolvedValueOnce({ status: "created", storyId: "story-2", story: {} });
    render(<StoryConfigUpload token="tok" onImported={vi.fn()} />);
    const text = JSON.stringify(VALID_NEW);

    await upload(text);
    await userEvent.type(screen.getByLabelText(/title/i), "A Brand New Tale");
    await userEvent.click(screen.getByRole("button", { name: /create story/i }));

    expect(importStoryConfiguration).toHaveBeenCalledWith("tok", {
      configurationText: text,
      title: "A Brand New Tale",
    });
  });

  it("surfaces a server rejection message verbatim", async () => {
    importStoryConfiguration.mockRejectedValueOnce({
      response: { status: 422, data: { error: "invalid_configuration", message: "characterTypes: duplicate character type name 'Archivist'" } },
    });
    render(<StoryConfigUpload token="tok" onImported={vi.fn()} />);

    await upload(JSON.stringify(VALID_OVERWRITE));
    await userEvent.click(screen.getByRole("button", { name: /^overwrite$/i }));

    expect(await screen.findByText(/duplicate character type name/i)).toBeInTheDocument();
  });

  it("rejects malformed JSON before sending any request, naming the position", async () => {
    render(<StoryConfigUpload token="tok" onImported={vi.fn()} />);

    await upload("{ not valid json");

    expect(await screen.findByText(/not valid json/i)).toBeInTheDocument();
    expect(screen.getByText(/position/i)).toBeInTheDocument();
    expect(importStoryConfiguration).not.toHaveBeenCalled();
  });

  it("rejects a payload that parses to something other than an object", async () => {
    render(<StoryConfigUpload token="tok" onImported={vi.fn()} />);

    await upload(JSON.stringify(["not", "an", "object"]));

    expect(await screen.findByText(/json object/i)).toBeInTheDocument();
    expect(importStoryConfiguration).not.toHaveBeenCalled();
  });

  it.each([
    ["worldPrompt", { ...VALID_NEW, worldPrompt: "" }],
    ["characterTypes", { ...VALID_NEW, characterTypes: [] }],
    ["completionCriteria.successConditions", { ...VALID_NEW, completionCriteria: { successConditions: [] } }],
  ])("rejects a missing/empty required key: %s", async (fieldName, payload) => {
    render(<StoryConfigUpload token="tok" onImported={vi.fn()} />);

    await upload(JSON.stringify(payload));

    expect(await screen.findByText(new RegExp(fieldName.split(".")[0]))).toBeInTheDocument();
    expect(importStoryConfiguration).not.toHaveBeenCalled();
  });

  it("rejects a missing name on the overwrite path", async () => {
    render(<StoryConfigUpload token="tok" onImported={vi.fn()} />);

    await upload(JSON.stringify({ ...VALID_OVERWRITE, name: undefined }));

    expect(await screen.findByText(/name.*required.*overwriting/i)).toBeInTheDocument();
    expect(importStoryConfiguration).not.toHaveBeenCalled();
  });

  it("does not pre-flight-reject content-rule cases — it posts them and shows what the server says", async () => {
    importStoryConfiguration.mockRejectedValueOnce({
      response: { status: 422, data: { error: "invalid_configuration", message: "notAField: unrecognised field" } },
    });
    render(<StoryConfigUpload token="tok" onImported={vi.fn()} />);

    await upload(JSON.stringify({ ...VALID_NEW, notAField: "oops" }));
    await userEvent.type(screen.getByLabelText(/title/i), "x");
    await userEvent.click(screen.getByRole("button", { name: /create story/i }));

    expect(importStoryConfiguration).toHaveBeenCalled();
    expect(await screen.findByText(/unrecognised field/i)).toBeInTheDocument();
  });
});
