"""Shared completion-rule evaluation for both real and test-play sessions
(010-story-test-play research.md Decision 3) — extracted from
`PlaySessionService._evaluate_completion`/`_rule_satisfied` so both session types enforce
identical rules rather than a second implementation. Reproduces that logic byte-for-byte;
`session` may be a `PlaySession` or a `TestPlaySession`, since both carry the same
`satisfiedSuccessConditions`/`satisfiedFailureConditions` fields."""

from __future__ import annotations

from typing import Any, Optional


def evaluate_completion(story, session, turn_data: dict[str, Any]) -> Optional[dict[str, Any]]:
    criteria = story.completionCriteria
    newly_success = turn_data.get("newlySatisfiedSuccessConditions", [])
    newly_failure = turn_data.get("newlySatisfiedFailureConditions", [])

    session.satisfiedSuccessConditions = sorted(set(session.satisfiedSuccessConditions) | set(newly_success))
    session.satisfiedFailureConditions = sorted(set(session.satisfiedFailureConditions) | set(newly_failure))

    success_ends = rule_satisfied(criteria.successConditions, session.satisfiedSuccessConditions, criteria.rule)
    failure_ends = rule_satisfied(criteria.failureConditions, session.satisfiedFailureConditions, criteria.rule)

    # Success is checked first: a same-turn tie is decided in success's favor (FR-009).
    if success_ends:
        detail_index = newly_success[0] if newly_success else session.satisfiedSuccessConditions[0]
        return {"type": "success", "detail": criteria.successConditions[detail_index]}
    if failure_ends:
        detail_index = newly_failure[0] if newly_failure else session.satisfiedFailureConditions[0]
        return {"type": "failure", "detail": criteria.failureConditions[detail_index]}
    return None


def rule_satisfied(configured: list[str], satisfied_indices: list[int], rule: Optional[str]) -> bool:
    if not configured:
        return False
    if rule == "all":
        return set(range(len(configured))) <= set(satisfied_indices)
    return len(satisfied_indices) > 0
