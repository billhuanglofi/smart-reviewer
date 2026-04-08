"""PR Improve tool – code improvement suggestions."""

from __future__ import annotations

import logging
from typing import Any

import yaml
from jinja2 import Environment, StrictUndefined

from smart_reviewer.ai_handler import AIHandler
from smart_reviewer.config import ReviewConfig
from smart_reviewer.github_client import GitHubClient
from smart_reviewer.prompts.improve import (
    IMPROVE_SYSTEM_PROMPT,
    IMPROVE_USER_PROMPT,
)

logger = logging.getLogger(__name__)

HEADER = "## 💡 Smart Suggestions"


class PRImprove:
    """Generate AI-powered code improvement suggestions.

    Parameters:
        config: Application configuration.
        github_client: Client for interacting with the PR.
        ai_handler: Client for LLM chat completions.
    """

    def __init__(
        self,
        config: ReviewConfig,
        github_client: GitHubClient,
        ai_handler: AIHandler,
    ) -> None:
        self.config = config
        self.github_client = github_client
        self.ai_handler = ai_handler

    async def run(self) -> str:
        """Execute the improve tool and optionally publish the result."""
        pr_info = self.github_client.get_pr_info()
        diff = self.github_client.get_pr_diff()

        env = Environment(undefined=StrictUndefined)
        system_prompt = IMPROVE_SYSTEM_PROMPT
        user_prompt = env.from_string(IMPROVE_USER_PROMPT).render(
            title=pr_info["title"],
            branch=pr_info["branch"],
            description=pr_info["body"],
            diff=diff,
            extra_instructions=self.config.extra_instructions,
        )

        raw = await self.ai_handler.chat_completion(system_prompt, user_prompt)
        data = _parse_yaml(raw)
        markdown = _format_markdown(data)

        if self.config.publish_output:
            self.github_client.publish_persistent_comment(markdown, HEADER)

        return markdown


def _parse_yaml(text: str) -> dict[str, Any]:
    """Parse YAML from the AI response, tolerating markdown fences."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines)
    try:
        result = yaml.safe_load(cleaned)
        if not isinstance(result, dict):
            return {}
        return result
    except yaml.YAMLError:
        logger.warning("Failed to parse YAML response from AI")
        return {}


def _format_markdown(data: dict[str, Any]) -> str:
    """Format parsed suggestion data into Markdown."""
    suggestions = data.get("code_suggestions") or []
    if not suggestions:
        return "### ✅ No improvement suggestions\n"

    parts: list[str] = []
    for idx, s in enumerate(suggestions, 1):
        fname = s.get("relevant_file", "")
        header = s.get("suggestion_header", "")
        content = s.get("suggestion_content", "")
        existing = s.get("existing_code", "").rstrip()
        improved = s.get("improved_code", "").rstrip()
        start = s.get("start_line", "")
        end = s.get("end_line", "")
        line_info = f" (lines {start}-{end})" if start and end else ""

        parts.append(f"### {idx}. {header}")
        parts.append(f"**File:** `{fname}`{line_info}\n")
        parts.append(f"{content}\n")
        parts.append(
            "<details><summary>💻 Code diff</summary>\n"
        )
        parts.append(f"**Existing code:**\n```\n{existing}\n```\n")
        parts.append(f"**Improved code:**\n```\n{improved}\n```\n")
        parts.append("</details>\n")

    return "\n".join(parts)
