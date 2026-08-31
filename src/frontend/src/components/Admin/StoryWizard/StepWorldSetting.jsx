import { useState } from "react";

import CharacterTypeList from "./CharacterTypeList.jsx";
import CompletionCriteriaFields from "./CompletionCriteriaFields.jsx";

/**
 * Tab 02 — world & setting (FR-003, FR-011). An optional one-shot "Suggest" action calls
 * the LLM once and injects the result into the editable, scrollable outline text box; it
 * is not an ongoing chat (replaces the earlier multi-turn ConversationPanel). A separate,
 * independently editable "rules" box, plus the dedicated character-type and
 * completion-criteria fields (FR-008), round out this tab.
 */
export function StepWorldSetting({ fields, onChange, onSuggestOutline }) {
  const [idea, setIdea] = useState("");
  const [suggestStatus, setSuggestStatus] = useState("idle"); // idle | suggesting | error

  const handleSuggest = async () => {
    if (!idea.trim()) return;
    setSuggestStatus("suggesting");
    try {
      const outline = await onSuggestOutline(idea);
      onChange({ outline });
      setSuggestStatus("idle");
    } catch {
      // The existing outline text box contents are left untouched on failure (Edge Cases)
      // so the administrator can retry Suggest or type the outline manually.
      setSuggestStatus("error");
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      <div className="field">
        <label htmlFor="outline-idea">Idea or guiding question for a suggested outline (optional)</label>
        <div style={{ display: "flex", gap: "10px" }}>
          <input
            id="outline-idea"
            className="input"
            value={idea}
            onChange={(event) => setIdea(event.target.value)}
            placeholder="A half-abandoned lighthouse on a cold northern cove in 1908…"
          />
          <button
            type="button"
            className="btn btn-secondary"
            onClick={handleSuggest}
            disabled={suggestStatus === "suggesting" || !idea.trim()}
          >
            {suggestStatus === "suggesting" ? "Suggesting…" : "Suggest"}
          </button>
        </div>
        {suggestStatus === "error" && (
          <div role="alert" className="text-muted" style={{ marginTop: "8px" }}>
            Could not generate a suggestion. Please try again, or write the outline yourself below.
          </div>
        )}
      </div>

      <div className="field">
        <label htmlFor="outline">Outline — what the story engine should know</label>
        <textarea
          id="outline"
          className="input"
          style={{ minHeight: "220px", overflowY: "auto" }}
          value={fields.outline}
          onChange={(event) => onChange({ outline: event.target.value })}
        />
      </div>

      <div className="field">
        <label htmlFor="rules">Rules the story must keep</label>
        <textarea
          id="rules"
          className="input"
          style={{ minHeight: "120px", overflowY: "auto" }}
          value={fields.rules}
          onChange={(event) => onChange({ rules: event.target.value })}
        />
      </div>

      <CharacterTypeList characterTypes={fields.characterTypes} onChange={(characterTypes) => onChange({ characterTypes })} />
      <CompletionCriteriaFields
        completionCriteria={fields.completionCriteria}
        onChange={(completionCriteria) => onChange({ completionCriteria })}
      />
    </div>
  );
}

export default StepWorldSetting;
