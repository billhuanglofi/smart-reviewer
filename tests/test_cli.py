"""Tests for the CLI module."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from smart_reviewer.cli import build_parser, main, run_cli


class TestBuildParser:
    """Tests for argument parsing."""

    def test_pr_url_required(self):
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args([])

    def test_pr_url_only(self):
        parser = build_parser()
        args = parser.parse_args(["https://github.com/owner/repo/pull/1"])
        assert args.pr_url == "https://github.com/owner/repo/pull/1"
        assert args.review is False
        assert args.describe is False
        assert args.improve is False
        assert args.publish is None
        assert args.model is None
        assert args.verbose is False

    def test_all_tool_flags(self):
        parser = build_parser()
        args = parser.parse_args([
            "--review", "--describe", "--improve",
            "https://github.com/o/r/pull/1",
        ])
        assert args.review is True
        assert args.describe is True
        assert args.improve is True

    def test_no_publish_flag(self):
        parser = build_parser()
        args = parser.parse_args([
            "--no-publish",
            "https://github.com/o/r/pull/1",
        ])
        assert args.publish is False

    def test_publish_flag(self):
        parser = build_parser()
        args = parser.parse_args([
            "--publish",
            "https://github.com/o/r/pull/1",
        ])
        assert args.publish is True

    def test_model_override(self):
        parser = build_parser()
        args = parser.parse_args([
            "--model", "gpt-3.5-turbo",
            "https://github.com/o/r/pull/1",
        ])
        assert args.model == "gpt-3.5-turbo"

    def test_verbose_flag(self):
        parser = build_parser()
        args = parser.parse_args(["-v", "https://github.com/o/r/pull/1"])
        assert args.verbose is True


class TestRunCli:
    """Tests for run_cli logic."""

    @pytest.fixture
    def _env(self, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "test-token")
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    @pytest.mark.asyncio
    @patch("smart_reviewer.cli.PRReviewer")
    @patch("smart_reviewer.cli.PRDescribe")
    @patch("smart_reviewer.cli.PRImprove")
    @patch("smart_reviewer.cli.GitHubClient")
    async def test_runs_all_tools_when_no_flags(
        self, mock_gh, mock_improve, mock_describe, mock_review, _env, capsys
    ):
        mock_review.return_value.run = AsyncMock(return_value="review output")
        mock_describe.return_value.run = AsyncMock(return_value="describe output")
        mock_improve.return_value.run = AsyncMock(return_value="improve output")

        parser = build_parser()
        args = parser.parse_args(["https://github.com/o/r/pull/1"])
        await run_cli(args)

        mock_review.return_value.run.assert_awaited_once()
        mock_describe.return_value.run.assert_awaited_once()
        mock_improve.return_value.run.assert_awaited_once()

        captured = capsys.readouterr()
        assert "review output" in captured.out
        assert "describe output" in captured.out
        assert "improve output" in captured.out

    @pytest.mark.asyncio
    @patch("smart_reviewer.cli.PRReviewer")
    @patch("smart_reviewer.cli.PRDescribe")
    @patch("smart_reviewer.cli.PRImprove")
    @patch("smart_reviewer.cli.GitHubClient")
    async def test_runs_only_selected_tool(
        self, mock_gh, mock_improve, mock_describe, mock_review, _env, capsys
    ):
        mock_review.return_value.run = AsyncMock(return_value="review output")

        parser = build_parser()
        args = parser.parse_args(["--review", "https://github.com/o/r/pull/1"])
        await run_cli(args)

        mock_review.return_value.run.assert_awaited_once()
        mock_describe.return_value.run.assert_not_called()
        mock_improve.return_value.run.assert_not_called()

    @pytest.mark.asyncio
    @patch("smart_reviewer.cli.PRReviewer")
    @patch("smart_reviewer.cli.PRDescribe")
    @patch("smart_reviewer.cli.PRImprove")
    @patch("smart_reviewer.cli.GitHubClient")
    async def test_model_override(
        self, mock_gh, mock_improve, mock_describe, mock_review, _env
    ):
        mock_review.return_value.run = AsyncMock(return_value="ok")

        parser = build_parser()
        args = parser.parse_args([
            "--review", "--model", "gpt-3.5-turbo",
            "https://github.com/o/r/pull/1",
        ])
        await run_cli(args)

        # Verify the config passed to PRReviewer has the overridden model
        config = mock_review.call_args[0][0]
        assert config.model == "gpt-3.5-turbo"

    @pytest.mark.asyncio
    @patch("smart_reviewer.cli.PRReviewer")
    @patch("smart_reviewer.cli.PRDescribe")
    @patch("smart_reviewer.cli.PRImprove")
    @patch("smart_reviewer.cli.GitHubClient")
    async def test_no_publish_override(
        self, mock_gh, mock_improve, mock_describe, mock_review, _env
    ):
        mock_review.return_value.run = AsyncMock(return_value="ok")

        parser = build_parser()
        args = parser.parse_args([
            "--review", "--no-publish",
            "https://github.com/o/r/pull/1",
        ])
        await run_cli(args)

        config = mock_review.call_args[0][0]
        assert config.publish_output is False

    @pytest.mark.asyncio
    async def test_missing_token_exits(self, monkeypatch):
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        parser = build_parser()
        args = parser.parse_args(["https://github.com/o/r/pull/1"])

        with pytest.raises(SystemExit):
            await run_cli(args)

    @pytest.mark.asyncio
    @patch("smart_reviewer.cli.GitHubClient", side_effect=ValueError("bad url"))
    async def test_invalid_pr_url_exits(self, mock_gh, _env):
        parser = build_parser()
        args = parser.parse_args(["https://not-a-valid-url"])

        with pytest.raises(SystemExit):
            await run_cli(args)

    @pytest.mark.asyncio
    @patch("smart_reviewer.cli.PRReviewer")
    @patch("smart_reviewer.cli.PRDescribe")
    @patch("smart_reviewer.cli.PRImprove")
    @patch("smart_reviewer.cli.GitHubClient")
    async def test_tool_exception_is_logged(
        self, mock_gh, mock_improve, mock_describe, mock_review, _env
    ):
        mock_review.return_value.run = AsyncMock(side_effect=RuntimeError("boom"))

        parser = build_parser()
        args = parser.parse_args(["--review", "https://github.com/o/r/pull/1"])
        # Should not raise - exceptions are caught and logged
        await run_cli(args)


class TestMain:
    """Tests for the main() entry point."""

    @patch("smart_reviewer.cli.run_cli", new_callable=AsyncMock)
    @patch("sys.argv", ["smart-reviewer", "https://github.com/o/r/pull/1"])
    def test_main_invokes_run_cli(self, mock_run_cli):
        main()
        mock_run_cli.assert_awaited_once()
