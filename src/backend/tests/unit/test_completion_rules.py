"""Unit tests for the shared completion-rule evaluation extracted from
PlaySessionService (010-story-test-play, T008) — covers `any`/`all` rules, the
success-before-failure tie, and the no-newly-satisfied-conditions case."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from backend.services.completion_rules import evaluate_completion, rule_satisfied


@dataclass
class _Criteria:
    successConditions: list[str]
    failureConditions: list[str] = field(default_factory=list)
    rule: Optional[str] = None


@dataclass
class _Story:
    completionCriteria: _Criteria


@dataclass
class _Session:
    satisfiedSuccessConditions: list[int] = field(default_factory=list)
    satisfiedFailureConditions: list[int] = field(default_factory=list)


# --- rule_satisfied ---


def test_rule_satisfied_is_false_when_nothing_configured():
    assert rule_satisfied([], [0], rule=None) is False


def test_rule_satisfied_any_rule_true_with_one_satisfied():
    assert rule_satisfied(["a", "b"], [0], rule="any") is True


def test_rule_satisfied_default_rule_behaves_like_any():
    assert rule_satisfied(["a", "b"], [1], rule=None) is True


def test_rule_satisfied_all_rule_false_until_every_index_satisfied():
    assert rule_satisfied(["a", "b"], [0], rule="all") is False


def test_rule_satisfied_all_rule_true_once_every_index_satisfied():
    assert rule_satisfied(["a", "b"], [0, 1], rule="all") is True


# --- evaluate_completion ---


def test_evaluate_completion_returns_none_when_nothing_newly_satisfied():
    story = _Story(completionCriteria=_Criteria(successConditions=["Find the keeper"]))
    session = _Session()

    result = evaluate_completion(story, session, {})

    assert result is None
    assert session.satisfiedSuccessConditions == []


def test_evaluate_completion_returns_success_when_condition_newly_satisfied():
    story = _Story(completionCriteria=_Criteria(successConditions=["Find the keeper"]))
    session = _Session()

    result = evaluate_completion(story, session, {"newlySatisfiedSuccessConditions": [0]})

    assert result == {"type": "success", "detail": "Find the keeper"}
    assert session.satisfiedSuccessConditions == [0]


def test_evaluate_completion_returns_failure_when_condition_newly_satisfied():
    story = _Story(
        completionCriteria=_Criteria(successConditions=["Find the keeper"], failureConditions=["Leave the cove"])
    )
    session = _Session()

    result = evaluate_completion(story, session, {"newlySatisfiedFailureConditions": [0]})

    assert result == {"type": "failure", "detail": "Leave the cove"}
    assert session.satisfiedFailureConditions == [0]


def test_evaluate_completion_success_wins_a_same_turn_tie():
    story = _Story(
        completionCriteria=_Criteria(successConditions=["Find the keeper"], failureConditions=["Leave the cove"])
    )
    session = _Session()

    result = evaluate_completion(
        story, session, {"newlySatisfiedSuccessConditions": [0], "newlySatisfiedFailureConditions": [0]}
    )

    assert result == {"type": "success", "detail": "Find the keeper"}


def test_evaluate_completion_all_rule_requires_every_condition():
    story = _Story(
        completionCriteria=_Criteria(successConditions=["Find the keeper", "Light the lamp"], rule="all")
    )
    session = _Session(satisfiedSuccessConditions=[0])

    result = evaluate_completion(story, session, {"newlySatisfiedSuccessConditions": [1]})

    assert result == {"type": "success", "detail": "Light the lamp"}
    assert session.satisfiedSuccessConditions == [0, 1]
