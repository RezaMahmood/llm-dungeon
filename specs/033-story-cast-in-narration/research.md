# Research: The Story's Cast Reaches the Narration

No NEEDS CLARIFICATION markers remain in the Technical Context — the spec was already clarified
and checklist-clean before planning. This records the two design decisions the plan depends on.

## Where the cast block is inserted

- **Decision**: Add the cast block to `_build_gameplay_turn_prompt` in
  `src/backend/services/llm_service.py`, immediately after the existing `Character: {name}
  ({type})` player line (line 472), listing every entry in `story.characterTypes` with its
  description where authored, under a heading distinct from the player line (e.g. `Cast:`).
- **Rationale**: `_build_gameplay_turn_prompt` already has `story` in scope, so no new data has to
  be threaded through `PlaySessionService` or `PlaySession`. Placing it beside the player line
  keeps the two "distinctly separate" (spec Acceptance Scenario 1) while requiring no change to
  session state.
- **Alternatives considered**: Storing a derived "cast summary" on `Story` or `PlaySession` at
  creation time — rejected: it would duplicate `characterTypes`, contradicting FR-004's "no
  change to the story configuration file" and the Assumption that the roster's stored shape does
  not change.

## How precedence is expressed to the narration

- **Decision**: Add a short instruction line alongside the cast block directing the narration to
  draw a named or story-significant character from the cast whenever an entry fits, while leaving
  incidental background figures open to invention — matching the clarification answer and FR-002
  verbatim rather than inventing new phrasing.
- **Rationale**: The existing prompt already carries similar directive lines (World, Rules,
  Narrative guidance, Tone); a precedence instruction in the same style is consistent with how the
  prompt already steers the LLM, and keeps the rule as one line rather than a structural constraint
  the code enforces (SC-002 assesses this by sampling a play-through, not by a deterministic
  check).
- **Alternatives considered**: Enforcing precedence in code (e.g. rejecting or rewriting narration
  that names a character not in the roster) — rejected: FR-002 explicitly frames this as a
  precedence rule the narration is directed to follow, not a closed cast list, and Assumption 3
  states narrative quality is judged by sampling, not a deterministic rule. Building an
  enforcement mechanism would also reach past this slice's scope (Out of Scope: "how the narration
  decides *when* a character appears").
