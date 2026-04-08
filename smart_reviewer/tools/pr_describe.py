"""PR Describe tool – auto-generate structured PR descriptions."""

from __future__ import annotations

import logging
from typing import Any

import yaml
from jinja2 import Environment, StrictUndefined

from smart_reviewer.ai_handler import AIHandler
from smart_reviewer.config import ReviewConfig
from smart_reviewer.github_client import GitHubClient
from smart_reviewer.prompts.describe import (
    DESCRIBE_SYSTEM_PROMPT,
    DESCRIBE_USER_PROMPT,
)

logger = logging.getLogger(__name__)

HEADER = "## 📝 Smart Description"

_TYPE_BADGES: dict[str, str] = {
    "Bug fix": "🐛 Bug fix",
    "Enhancement": "✨ Enhancement",
    "Refactoring": "♻️ Refactoring",
    "Documentation": "📖 Documentation",
    "Tests": "🧪 Tests",
    "Configuration": "⚙️ Configuration",
    "Other": "🔧 Other",
}


class PRDescribe:
    """Generate an AI-powered PR description.

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
        """Execute the describe tool and optionally publish the result."""
        pr_info = self.github_client.get_pr_info()
        diff = self.github_client.get_pr_diff()
        commit_messages = self.github_client.get_commit_messages()

        env = Environment(undefined=StrictUndefined)
        system_prompt = DESCRIBE_SYSTEM_PROMPT
        user_prompt = env.from_string(DESCRIBE_USER_PROMPT).render(
            title=pr_info["title"],
            branch=pr_info["branch"],
            diff=diff,
            commit_messages=commit_messages,
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
    """Format parsed describe data into Markdown."""
    parts: list[str] = []

    pr_type = data.get("type", "Other")
    badge = _TYPE_BADGES.get(pr_type, f"🔧 {pr_type}")
    parts.append(f"### {badge}\n")

    description = data.get("description", "")
    if description:
        parts.append(f"{description}\n")

    walkthrough = data.get("main_files_walkthrough") or []
    if walkthrough:
        parts.append(
            "<details><summary>📁 Files walkthrough</summary>\n"
        )
        parts.append("| File | Changes |")
        parts.append("|------|---------|")
        for entry in walkthrough:
            fname = entry.get("filename", "")
            summary = entry.get("changes_summary", "")
            parts.append(f"| `{fname}` | {summary} |")
        parts.append("\n</details>")

    return "\n".join(parts)
