import { useEffect, useState } from "react";

/**
 * Repeatable add/remove rows for character types (FR-008). Edits to name/description
 * commit to the parent (and so the backend, via PATCH) on blur, not per keystroke — a
 * newly added row is local-only until its name is filled in and blurred, so it never
 * round-trips an empty (invalid) name to the draft.
 */
export function CharacterTypeList({ characterTypes = [], onChange }) {
  const [rows, setRows] = useState(characterTypes);

  useEffect(() => {
    setRows(characterTypes);
  }, [characterTypes]);

  const updateRow = (index, field, value) => {
    setRows((current) => current.map((row, i) => (i === index ? { ...row, [field]: value } : row)));
  };

  const commitRow = (index) => {
    const row = rows[index];
    if (!row.name.trim()) return; // not yet valid — wait for the admin to fill in a name
    onChange(rows);
  };

  const addRow = () => {
    setRows((current) => [...current, { name: "", description: "" }]);
  };

  const removeRow = (index) => {
    const next = rows.filter((_, i) => i !== index);
    setRows(next);
    onChange(next);
  };

  return (
    <div className="field">
      <label>Character types</label>
      {rows.map((row, index) => (
        <div key={index} style={{ display: "flex", gap: "10px", marginBottom: "8px" }}>
          <input
            className="input"
            aria-label="Character name"
            value={row.name}
            onChange={(event) => updateRow(index, "name", event.target.value)}
            onBlur={() => commitRow(index)}
            placeholder="Name"
          />
          <input
            className="input"
            aria-label="Character description"
            value={row.description || ""}
            onChange={(event) => updateRow(index, "description", event.target.value)}
            onBlur={() => commitRow(index)}
            placeholder="Description (optional)"
          />
          <button type="button" className="btn btn-secondary" onClick={() => removeRow(index)}>
            Remove
          </button>
        </div>
      ))}
      <button type="button" className="btn btn-secondary" onClick={addRow}>
        Add character type
      </button>
    </div>
  );
}

export default CharacterTypeList;
