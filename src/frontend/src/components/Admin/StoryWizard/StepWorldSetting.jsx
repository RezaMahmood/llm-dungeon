import { useEffect, useState } from "react";

import CharacterTypeList from "./CharacterTypeList.jsx";
import CompletionCriteriaFields from "./CompletionCriteriaFields.jsx";
import ConversationPanel from "./ConversationPanel.jsx";

export function StepWorldSetting({ draft, onSendMessage, onPatch, fieldErrors = {} }) {
  const [worldPrompt, setWorldPrompt] = useState(draft.worldPrompt || "");
  const [rules, setRules] = useState(draft.rules || "");

  useEffect(() => setWorldPrompt(draft.worldPrompt || ""), [draft.worldPrompt]);
  useEffect(() => setRules(draft.rules || ""), [draft.rules]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      <ConversationPanel exchanges={draft.exchanges} onSendMessage={onSendMessage} />

      <div className="field">
        <label htmlFor="world-prompt">World prompt — what the story engine should know</label>
        <textarea
          id="world-prompt"
          className="input"
          value={worldPrompt}
          onChange={(event) => setWorldPrompt(event.target.value)}
          onBlur={() => {
            if (worldPrompt !== (draft.worldPrompt || "")) onPatch({ worldPrompt });
          }}
        />
        {fieldErrors.worldPrompt && (
          <div role="alert" className="text-muted">
            {fieldErrors.worldPrompt}
          </div>
        )}
      </div>

      <div className="field">
        <label htmlFor="rules">Rules the story must keep</label>
        <textarea
          id="rules"
          className="input"
          value={rules}
          onChange={(event) => setRules(event.target.value)}
          onBlur={() => {
            if (rules !== (draft.rules || "")) onPatch({ rules });
          }}
        />
        {fieldErrors.rules && (
          <div role="alert" className="text-muted">
            {fieldErrors.rules}
          </div>
        )}
      </div>

      <CharacterTypeList
        characterTypes={draft.characterTypes || []}
        onChange={(characterTypes) => onPatch({ characterTypes })}
        error={fieldErrors.characterTypes}
      />
      <CompletionCriteriaFields
        completionCriteria={draft.completionCriteria}
        onChange={(completionCriteria) => onPatch({ completionCriteria })}
        error={fieldErrors.completionCriteria}
      />
    </div>
  );
}

export default StepWorldSetting;
