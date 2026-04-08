"""Prompt templates for Smart Reviewer tools."""

from smart_reviewer.prompts.review import REVIEW_SYSTEM_PROMPT, REVIEW_USER_PROMPT
from smart_reviewer.prompts.describe import DESCRIBE_SYSTEM_PROMPT, DESCRIBE_USER_PROMPT
from smart_reviewer.prompts.improve import IMPROVE_SYSTEM_PROMPT, IMPROVE_USER_PROMPT

__all__ = [
    "REVIEW_SYSTEM_PROMPT",
    "REVIEW_USER_PROMPT",
    "DESCRIBE_SYSTEM_PROMPT",
    "DESCRIBE_USER_PROMPT",
    "IMPROVE_SYSTEM_PROMPT",
    "IMPROVE_USER_PROMPT",
]
