import { useEffect, useState } from "react";

function emptyCriteria() {
  return { maxDurationMinutes: null, successConditions: [], failureConditions: [], rule: null };
}

/**
 * Optional max-duration input, success/failure condition rows, and an any/all rule
 * selector shown only once more than one condition is defined (data-model.md Completion
 * Criteria). Edits commit to the parent on blur/change of a completed field; removing the
 * last success condition clears the whole structure back to `null` rather than sending an
 * invalid empty-successConditions object (the shared structure requires at least one).
 */
export function CompletionCriteriaFields({ completionCriteria, onChange, error }) {
  const [criteria, setCriteria] = useState(completionCriteria || emptyCriteria());

  useEffect(() => {
    setCriteria(completionCriteria || emptyCriteria());
  }, [completionCriteria]);

  const totalConditions = criteria.successConditions.length + criteria.failureConditions.length;

  const commit = (next) => {
    // The shared structure requires `rule` once more than one condition is defined
    // (data-model.md Completion Criteria). Default to "any" so committing a second
    // condition (e.g. blurring it right after typing) is always valid — the admin can
    // still switch to "All" via the selector below, which just re-commits. Without this,
    // adding a failure/success condition past the first one round-tripped an invalid
    // payload and the write was rejected with a 422 the admin never saw (no error was
    // surfaced on this component) — see #33 follow-up.
    const total = next.successConditions.length + next.failureConditions.length;
    const withRule = total > 1 && !next.rule ? { ...next, rule: "any" } : next;
    setCriteria(withRule);
    onChange(withRule.successConditions.length > 0 ? withRule : null);
  };

  const updateConditionList = (key, index, value) => {
    setCriteria((current) => ({
      ...current,
      [key]: current[key].map((condition, i) => (i === index ? value : condition)),
    }));
  };

  const commitConditionList = (key, index) => {
    const value = criteria[key][index];
    if (!value.trim()) return;
    commit(criteria);
  };

  const addCondition = (key) => {
    setCriteria((current) => ({ ...current, [key]: [...current[key], ""] }));
  };

  const removeCondition = (key, index) => {
    commit({ ...criteria, [key]: criteria[key].filter((_, i) => i !== index) });
  };

  const updateMaxDuration = (value) => {
    commit({ ...criteria, maxDurationMinutes: value ? Number(value) : null });
  };

  const updateRule = (rule) => {
    commit({ ...criteria, rule });
  };

  return (
    <div className="field">
      <label>Completion criteria</label>

      <div className="field">
        <label htmlFor="max-duration">Maximum session duration (minutes, optional)</label>
        <input
          id="max-duration"
          className="input"
          type="number"
          value={criteria.maxDurationMinutes ?? ""}
          onChange={(event) => updateMaxDuration(event.target.value)}
        />
      </div>

      <div className="field">
        <label>Success conditions</label>
        {criteria.successConditions.map((condition, index) => (
          <div key={index} style={{ display: "flex", gap: "10px", marginBottom: "8px" }}>
            <input
              className="input"
              aria-label="Success condition"
              value={condition}
              onChange={(event) => updateConditionList("successConditions", index, event.target.value)}
              onBlur={() => commitConditionList("successConditions", index)}
            />
            <button type="button" className="btn btn-secondary" onClick={() => removeCondition("successConditions", index)}>
              Remove
            </button>
          </div>
        ))}
        <button type="button" className="btn btn-secondary" onClick={() => addCondition("successConditions")}>
          Add success condition
        </button>
      </div>

      <div className="field">
        <label>Failure conditions (optional)</label>
        {criteria.failureConditions.map((condition, index) => (
          <div key={index} style={{ display: "flex", gap: "10px", marginBottom: "8px" }}>
            <input
              className="input"
              aria-label="Failure condition"
              value={condition}
              onChange={(event) => updateConditionList("failureConditions", index, event.target.value)}
              onBlur={() => commitConditionList("failureConditions", index)}
            />
            <button type="button" className="btn btn-secondary" onClick={() => removeCondition("failureConditions", index)}>
              Remove
            </button>
          </div>
        ))}
        <button type="button" className="btn btn-secondary" onClick={() => addCondition("failureConditions")}>
          Add failure condition
        </button>
      </div>

      {totalConditions > 1 && (
        <div className="field">
          <label>How should multiple conditions combine?</label>
          <div className="seg">
            <label className="seg-opt">
              <input type="radio" name="completion-rule" checked={criteria.rule === "any"} onChange={() => updateRule("any")} />
              <span>Any</span>
            </label>
            <label className="seg-opt">
              <input type="radio" name="completion-rule" checked={criteria.rule === "all"} onChange={() => updateRule("all")} />
              <span>All</span>
            </label>
          </div>
        </div>
      )}
      {error && (
        <div role="alert" className="text-muted">
          {error}
        </div>
      )}
    </div>
  );
}

export default CompletionCriteriaFields;
