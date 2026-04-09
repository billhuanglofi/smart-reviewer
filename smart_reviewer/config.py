"""Configuration for Smart Reviewer loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


_UNSET = object()


def _env_bool(key: str, default: bool = False) -> bool:
    """Read an environment variable as a boolean.

    If the variable is not present in the environment the *default* is
    returned.  Otherwise ``"true"`` and ``"1"`` (case-insensitive) are
    treated as ``True``; every other value — including the empty string —
    is ``False``.
    """
    value = os.environ.get(key, _UNSET)
    if value is _UNSET:
        return default
    return value.lower() in ("true", "1")


@dataclass
class ReviewConfig:
    """Configuration loaded from environment variables."""

    github_token: str
    openai_api_key: str = ""
    model: str = "gpt-4o"
    max_tokens: int = 4096
    temperature: float = 0.2
    auto_review: bool = True
    auto_describe: bool = True
    auto_improve: bool = True
    extra_instructions: str = ""
    num_max_findings: int = 3
    require_security_review: bool = True
    require_effort_estimation: bool = True
    publish_output: bool = True
    include_past_reviews: bool = True
    github_api_url: str = ""
    llm_api_base: str = ""
    ssl_verify: bool = True

    @classmethod
    def from_env(cls) -> ReviewConfig:
        """Create a :class:`ReviewConfig` from the current environment.

        Raises:
            ValueError: If ``GITHUB_TOKEN`` is not set.
        """
        github_token = os.environ.get("GITHUB_TOKEN", "")
        if not github_token:
            raise ValueError("GITHUB_TOKEN environment variable is required")

        return cls(
            github_token=github_token,
            openai_api_key=os.environ.get("OPENAI_API_KEY", ""),
            model=os.environ.get("LLM_MODEL", "gpt-4o"),
            max_tokens=int(os.environ.get("MAX_TOKENS", "4096")),
            temperature=float(os.environ.get("TEMPERATURE", "0.2")),
            auto_review=_env_bool("AUTO_REVIEW", default=True),
            auto_describe=_env_bool("AUTO_DESCRIBE", default=True),
            auto_improve=_env_bool("AUTO_IMPROVE", default=True),
            extra_instructions=os.environ.get("EXTRA_INSTRUCTIONS", ""),
            num_max_findings=int(os.environ.get("NUM_MAX_FINDINGS", "3")),
            require_security_review=_env_bool(
                "REQUIRE_SECURITY_REVIEW", default=True
            ),
            require_effort_estimation=_env_bool(
                "REQUIRE_EFFORT_ESTIMATION", default=True
            ),
            publish_output=_env_bool("PUBLISH_OUTPUT", default=True),
            include_past_reviews=_env_bool(
                "INCLUDE_PAST_REVIEWS", default=True
            ),
            github_api_url=os.environ.get("GITHUB_API_URL", ""),
            llm_api_base=os.environ.get("LLM_API_BASE", ""),
            ssl_verify=_env_bool("SSL_VERIFY", default=True),
        )
