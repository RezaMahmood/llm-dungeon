"""AvatarValidationService — validates a player's free-text avatar description before a
play session is created (032-story-archetypes-player-avatar FR-001, FR-006-FR-017).

Order matters: the cost-free checks (blank, length) run first and never touch the
attempt cap or spend a token (FR-010); only reaching the model-backed check increments
the attempt counter and, once the call completes, accrues its tokens to the adventure's
total (FR-016) — rejections included, since a verdict of either kind still means the
call ran and spent tokens."""

from __future__ import annotations

from typing import Optional

from backend.services.avatar_setup_attempts_service import AvatarSetupAttemptsService
from backend.services.llm_service import AvatarRelevanceCheckUnavailableError, LLMService
from backend.services.story_service import StoryService

MIN_AVATAR_DESCRIPTION_LENGTH = 20
MAX_AVATAR_DESCRIPTION_LENGTH = 500

# A guard rail, not a quota to tune (spec.md Assumptions) — high enough that a player
# genuinely rewriting their description is never stopped, low enough that sustained
# probing is.
MAX_MODEL_BACKED_ATTEMPTS = 5


class AvatarDescriptionBlankError(Exception):
    """FR-006: the description was empty or whitespace-only."""


class AvatarDescriptionTooShortError(Exception):
    """FR-006: shorter than MIN_AVATAR_DESCRIPTION_LENGTH after trimming."""


class AvatarDescriptionTooLongError(Exception):
    """FR-006: longer than MAX_AVATAR_DESCRIPTION_LENGTH after trimming."""


class AvatarDescriptionNotStoryRelevantError(Exception):
    """FR-007/FR-008: the model-backed check judged this not to be a story-relevant
    character description, or one that reads as an instruction to the narration."""


class AvatarDescriptionCheckUnavailableError(Exception):
    """FR-012: the model-backed check could not reach a verdict — timed out or errored.
    Distinguishable from AvatarDescriptionNotStoryRelevantError so the player is told the
    check could not complete, not that their description was judged non-conforming."""


class AvatarValidationAttemptsExceededError(Exception):
    """FR-014: the model-backed attempt cap was reached for this (player, story) setup."""


class AvatarValidationService:
    def __init__(
        self,
        llm_service: Optional[LLMService] = None,
        attempts_service: Optional[AvatarSetupAttemptsService] = None,
        story_service: Optional[StoryService] = None,
    ) -> None:
        self._llm = llm_service or LLMService()
        self._attempts = attempts_service or AvatarSetupAttemptsService()
        self._stories = story_service or StoryService()

    def validate(self, description: str, player_id: str, story_id: str) -> str:
        """Returns the trimmed, validated description, or raises one of the errors above.
        Equivalent to `validate_relevance(validate_format(description), ...)` — kept as a
        single call for a caller with no need to interleave its own field checks (e.g. the
        character name's) between the two phases."""
        return self.validate_relevance(self.validate_format(description), player_id, story_id)

    def validate_format(self, description: str) -> str:
        """The cost-free checks alone (FR-006, FR-010): blank, then the 20-500 character
        bounds. Spends no token and touches no attempt cap. Returns the trimmed
        description."""
        trimmed = description.strip()
        if not trimmed:
            raise AvatarDescriptionBlankError()
        if len(trimmed) < MIN_AVATAR_DESCRIPTION_LENGTH:
            raise AvatarDescriptionTooShortError()
        if len(trimmed) > MAX_AVATAR_DESCRIPTION_LENGTH:
            raise AvatarDescriptionTooLongError()
        return trimmed

    def validate_relevance(self, trimmed_description: str, player_id: str, story_id: str) -> str:
        """The model-backed check alone (FR-007, FR-008), for a description that has
        already passed `validate_format`. Increments the attempt counter before the call
        and accrues its tokens to the adventure's total once it completes, whatever the
        verdict (FR-014, FR-016)."""
        if self._attempts.get_attempts(player_id, story_id) >= MAX_MODEL_BACKED_ATTEMPTS:
            raise AvatarValidationAttemptsExceededError()
        self._attempts.record_attempt(player_id, story_id)

        try:
            is_valid, tokens_used = self._llm.check_avatar_description(trimmed_description)
        except AvatarRelevanceCheckUnavailableError as exc:
            raise AvatarDescriptionCheckUnavailableError() from exc

        self._stories.record_avatar_validation_tokens(story_id, tokens_used)

        if not is_valid:
            raise AvatarDescriptionNotStoryRelevantError()

        return trimmed_description

    def clear_attempts(self, player_id: str, story_id: str) -> None:
        """Called once a session is successfully created, so a later, separate setup
        against the same adventure starts fresh."""
        self._attempts.clear(player_id, story_id)
