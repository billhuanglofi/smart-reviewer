"""PR Reviewer tool – key issues, security concerns, effort estimation."""

from __future__ import annotations

import logging
from typing import Any

import yaml
from jinja2 import Environment, StrictUndefined

from smart_reviewer.ai_handler import AIHandler
from smart_reviewer.config import ReviewConfig
from smart_reviewer.github_client import GitHubClient
from smart_reviewer.prompts.review import REVIEW_SYSTEM_PROMPT, REVIEW_USER_PROMPT

logger = logging.getLogger(__name__)

HEADER = "## 🔍 Smart Review"

_EFFORT_BADGES = {
    1: "🟢 Trivial (1/5)",
    2: "🟡 Low (2/5)",
    3: "🟠 Moderate (3/5)",
    4: "🔴 High (4/5)",
    5: "⛔ Very High (5/5)",
}


class PRReviewer:
    """Run an AI-powered code review on a pull request.

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
        """Execute the review and optionally publish the result."""
        pr_info = self.github_client.get_pr_info()
        diff = self.github_client.get_pr_diff()
        self.github_client.get_pr_files()  # pre-fetch for context

        env = Environment(undefined=StrictUndefined)
        system_prompt = REVIEW_SYSTEM_PROMPT
        user_prompt = env.from_string(REVIEW_USER_PROMPT).render(
            title=pr_info["title"],
            branch=pr_info["branch"],
            description=pr_info["body"],
            diff=diff,
            num_max_findings=self.config.num_max_findings,
            require_security_review=self.config.require_security_review,
            require_effort_estimation=self.config.require_effort_estimation,
            extra_instructions=self.config.extra_instructions,
        )

        raw = await self.ai_handler.chat_completion(system_prompt, user_prompt)
        data = _parse_yaml(raw)
        markdown = _format_markdown(data, self.config)

        if self.config.publish_output:
            self.github_client.publish_persistent_comment(markdown, HEADER)

        return markdown


def _parse_yaml(text: str) -> dict[str, Any]:
    """Parse YAML from the AI response, tolerating markdown fences."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        lines = lines[1:]  # drop opening fence
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


def _format_markdown(data: dict[str, Any], config: ReviewConfig) -> str:
    """Format parsed review data into Markdown."""
    parts: list[str] = []

    # Effort estimation
    if config.require_effort_estimation:
        effort = data.get("estimated_effort_to_review", "N/A")
        badge = _EFFORT_BADGES.get(effort, f"Unknown ({effort})")
        parts.append(f"### ⏱️ Estimated effort to review: {badge}\n")

    # Key issues
    issues = data.get("key_issues_to_review") or []
    if issues:
        parts.append("### 🔑 Key issues\n")
        parts.append("| # | File | Issue | Lines |")
        parts.append("|---|------|-------|-------|")
        for idx, issue in enumerate(issues, 1):
            fname = issue.get("relevant_file", "")
            header = issue.get("issue_header", "")
            content = issue.get("issue_content", "")
            start = issue.get("start_line", "")
            end = issue.get("end_line", "")
            line_range = f"L{start}-L{end}" if start and end else ""
            parts.append(
                f"| {idx} | `{fname}` | **{header}** – {content} | {line_range} |"
            )
        parts.append("")
    else:
        parts.append("### ✅ No critical issues found\n")

    # Security
    if config.require_security_review:
        security = data.get("security_concerns", "")
        if security:
            parts.append("### 🔒 Security concerns\n")
            parts.append(f"{security}\n")
        else:
            parts.append("### 🔒 No security concerns identified\n")

    return "\n".join(parts)
