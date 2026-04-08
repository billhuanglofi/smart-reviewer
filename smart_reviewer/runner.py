"""GitHub Action runner entry point for Smart Reviewer."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys

from smart_reviewer.ai_handler import AIHandler
from smart_reviewer.config import ReviewConfig
from smart_reviewer.github_client import GitHubClient
from smart_reviewer.tools.pr_describe import PRDescribe
from smart_reviewer.tools.pr_improve import PRImprove
from smart_reviewer.tools.pr_reviewer import PRReviewer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _build_pr_url(event: dict) -> str | None:
    """Extract the PR HTML URL from the GitHub event payload."""
    pr = event.get("pull_request")
    if pr:
        return pr.get("html_url")
    # issue_comment events carry the issue URL
    issue = event.get("issue", {})
    pr_data = issue.get("pull_request")
    if pr_data:
        return pr_data.get("html_url")
    return None


def _parse_command(event: dict) -> str | None:
    """Return a slash command from an issue_comment body, if any."""
    comment = event.get("comment", {})
    body: str = comment.get("body", "").strip()
    for cmd in ("/review", "/describe", "/improve"):
        if body.startswith(cmd):
            return cmd
    return None


async def run_action() -> None:
    """Main entry point – read the GitHub event and dispatch tools."""
    try:
        config = ReviewConfig.from_env()
    except ValueError as exc:
        logger.error("Configuration error: %s", exc)
        sys.exit(1)

    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    event_path = os.environ.get("GITHUB_EVENT_PATH", "")

    if not event_path or not os.path.isfile(event_path):
        logger.error("GITHUB_EVENT_PATH is not set or file does not exist")
        sys.exit(1)

    with open(event_path, encoding="utf-8") as fh:
        event = json.load(fh)

    pr_url = _build_pr_url(event)
    if not pr_url:
        logger.info("No pull request found in event payload – nothing to do.")
        return

    github_client = GitHubClient(config.github_token, pr_url)
    ai_handler = AIHandler(config)

    if event_name == "pull_request":
        action = event.get("action", "")
        if action not in ("opened", "synchronize", "reopened"):
            logger.info("Ignoring pull_request action: %s", action)
            return
        await _run_auto_tools(config, github_client, ai_handler)

    elif event_name == "issue_comment":
        command = _parse_command(event)
        if command:
            await _run_command(command, config, github_client, ai_handler)
        else:
            logger.info("Comment does not contain a recognised command.")
    else:
        logger.info("Unhandled event: %s", event_name)


async def _run_auto_tools(
    config: ReviewConfig,
    github_client: GitHubClient,
    ai_handler: AIHandler,
) -> None:
    """Run the tools that are enabled for automatic execution."""
    tasks: list[asyncio.Task[str]] = []

    if config.auto_review:
        reviewer = PRReviewer(config, github_client, ai_handler)
        tasks.append(asyncio.create_task(reviewer.run()))
    if config.auto_describe:
        describer = PRDescribe(config, github_client, ai_handler)
        tasks.append(asyncio.create_task(describer.run()))
    if config.auto_improve:
        improver = PRImprove(config, github_client, ai_handler)
        tasks.append(asyncio.create_task(improver.run()))

    for task in tasks:
        try:
            await task
        except Exception:
            logger.exception("Tool execution failed")


async def _run_command(
    command: str,
    config: ReviewConfig,
    github_client: GitHubClient,
    ai_handler: AIHandler,
) -> None:
    """Run a single tool triggered by a slash command."""
    tool_map = {
        "/review": lambda: PRReviewer(config, github_client, ai_handler),
        "/describe": lambda: PRDescribe(config, github_client, ai_handler),
        "/improve": lambda: PRImprove(config, github_client, ai_handler),
    }
    factory = tool_map.get(command)
    if factory is None:
        logger.warning("Unknown command: %s", command)
        return

    tool = factory()
    try:
        await tool.run()
    except Exception:
        logger.exception("Tool %s failed", command)


if __name__ == "__main__":
    asyncio.run(run_action())
