"""Local CLI entry point for Smart Reviewer.

Usage examples:

    # Review a PR (all tools)
    smart-reviewer https://github.com/owner/repo/pull/42

    # Run only specific tools
    smart-reviewer --review https://github.com/owner/repo/pull/42
    smart-reviewer --describe --improve https://github.com/owner/repo/pull/42

    # Disable publishing (print output to stdout only)
    smart-reviewer --no-publish https://github.com/owner/repo/pull/42

Environment variables:
    GITHUB_TOKEN      GitHub personal access token (required)
    OPENAI_API_KEY    OpenAI API key (required for AI features)
    LLM_MODEL         Model to use (default: gpt-4o)
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from smart_reviewer.ai_handler import AIHandler
from smart_reviewer.config import ReviewConfig
from smart_reviewer.github_client import GitHubClient
from smart_reviewer.tools.pr_describe import PRDescribe
from smart_reviewer.tools.pr_improve import PRImprove
from smart_reviewer.tools.pr_reviewer import PRReviewer

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="smart-reviewer",
        description="AI-powered pull request review, description, and improvement suggestions.",
    )
    parser.add_argument(
        "pr_url",
        help="Full URL to the GitHub pull request (e.g. https://github.com/owner/repo/pull/42)",
    )
    parser.add_argument(
        "--review",
        action="store_true",
        default=False,
        help="Run the review tool",
    )
    parser.add_argument(
        "--describe",
        action="store_true",
        default=False,
        help="Run the describe tool",
    )
    parser.add_argument(
        "--improve",
        action="store_true",
        default=False,
        help="Run the improve tool",
    )
    parser.add_argument(
        "--publish",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Publish results as PR comments (default: true). Use --no-publish to only print to stdout.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="LLM model to use (overrides LLM_MODEL env var)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        default=False,
        help="Enable verbose (debug) logging",
    )
    return parser


async def run_cli(args: argparse.Namespace) -> None:
    """Execute the CLI with the parsed arguments."""
    try:
        config = ReviewConfig.from_env()
    except ValueError as exc:
        logger.error("Configuration error: %s", exc)
        sys.exit(1)

    # CLI flag overrides
    if args.model is not None:
        config.model = args.model
    if args.publish is not None:
        config.publish_output = args.publish

    # If no specific tool flag is set, run all enabled tools
    run_review = args.review
    run_describe = args.describe
    run_improve = args.improve
    if not any([run_review, run_describe, run_improve]):
        run_review = config.auto_review
        run_describe = config.auto_describe
        run_improve = config.auto_improve

    try:
        github_client = GitHubClient(
            config.github_token,
            args.pr_url,
            api_url=config.github_api_url,
            ssl_verify=config.ssl_verify,
        )
    except ValueError as exc:
        logger.error("Invalid PR URL: %s", exc)
        sys.exit(1)

    ai_handler = AIHandler(config)

    tasks: list[tuple[str, asyncio.Task[str]]] = []
    if run_review:
        reviewer = PRReviewer(config, github_client, ai_handler)
        tasks.append(("Review", asyncio.create_task(reviewer.run())))
    if run_describe:
        describer = PRDescribe(config, github_client, ai_handler)
        tasks.append(("Describe", asyncio.create_task(describer.run())))
    if run_improve:
        improver = PRImprove(config, github_client, ai_handler)
        tasks.append(("Improve", asyncio.create_task(improver.run())))

    if not tasks:
        logger.info("No tools selected to run.")
        return

    for name, task in tasks:
        try:
            result = await task
            print(f"\n{'=' * 60}")
            print(f"  {name}")
            print(f"{'=' * 60}\n")
            print(result)
        except Exception:
            logger.exception("Tool '%s' failed", name)


def main() -> None:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    asyncio.run(run_cli(args))


if __name__ == "__main__":
    main()
