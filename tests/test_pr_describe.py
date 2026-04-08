"""Tests for PRDescribe tool."""

from __future__ import annotations

from unittest import mock

import pytest

from smart_reviewer.config import ReviewConfig
from smart_reviewer.tools.pr_describe import PRDescribe, _format_markdown, _parse_yaml

SAMPLE_YAML = """\
type: "Enhancement"
description: "Added user authentication module"
main_files_walkthrough:
  - filename: "src/auth.py"
    changes_summary: "New authentication middleware"
  - filename: "tests/test_auth.py"
    changes_summary: "Tests for authentication"
"""


def _make_config(**overrides) -> ReviewConfig:
    defaults = {
        "github_token": "tok",
        "openai_api_key": "sk-test",
        "model": "gpt-4o",
        "max_tokens": 100,
        "temperature": 0.1,
        "publish_output": False,
    }
    defaults.update(overrides)
    return ReviewConfig(**defaults)


class TestParseYaml:
    def test_valid_yaml(self):
        data = _parse_yaml(SAMPLE_YAML)
        assert data["type"] == "Enhancement"
        assert len(data["main_files_walkthrough"]) == 2

    def test_yaml_with_fences(self):
        fenced = f"```yaml\n{SAMPLE_YAML}\n```"
        data = _parse_yaml(fenced)
        assert data["type"] == "Enhancement"

    def test_malformed_yaml(self):
        assert _parse_yaml("{{{bad") == {}

    def test_non_dict_yaml(self):
        assert _parse_yaml("- a\n- b") == {}


class TestFormatMarkdown:
    def test_includes_type_badge(self):
        data = _parse_yaml(SAMPLE_YAML)
        md = _format_markdown(data)
        assert "Enhancement" in md

    def test_includes_description(self):
        data = _parse_yaml(SAMPLE_YAML)
        md = _format_markdown(data)
        assert "user authentication" in md

    def test_includes_walkthrough_table(self):
        data = _parse_yaml(SAMPLE_YAML)
        md = _format_markdown(data)
        assert "src/auth.py" in md
        assert "test_auth.py" in md

    def test_empty_walkthrough(self):
        data = {"type": "Other", "description": "x", "main_files_walkthrough": []}
        md = _format_markdown(data)
        assert "Other" in md
        # No table expected
        assert "File" not in md


class TestPRDescribeRun:
    @pytest.mark.asyncio
    async def test_full_flow(self):
        config = _make_config(publish_output=False)
        mock_gh = mock.MagicMock()
        mock_gh.get_pr_info.return_value = {
            "title": "Add auth",
            "body": "Auth module",
            "branch": "feat/auth",
            "base_branch": "main",
            "author": "bob",
            "created_at": "2025-01-01",
        }
        mock_gh.get_pr_diff.return_value = "diff"
        mock_gh.get_commit_messages.return_value = "Add auth module"

        mock_ai = mock.MagicMock()
        mock_ai.chat_completion = mock.AsyncMock(return_value=SAMPLE_YAML)

        describer = PRDescribe(config, mock_gh, mock_ai)
        result = await describer.run()

        assert "Enhancement" in result
        assert "src/auth.py" in result
        mock_ai.chat_completion.assert_called_once()

    @pytest.mark.asyncio
    async def test_publishes_when_enabled(self):
        config = _make_config(publish_output=True)
        mock_gh = mock.MagicMock()
        mock_gh.get_pr_info.return_value = {
            "title": "T", "body": "", "branch": "b",
            "base_branch": "m", "author": "a", "created_at": "t",
        }
        mock_gh.get_pr_diff.return_value = ""
        mock_gh.get_commit_messages.return_value = ""

        mock_ai = mock.MagicMock()
        mock_ai.chat_completion = mock.AsyncMock(return_value=SAMPLE_YAML)

        describer = PRDescribe(config, mock_gh, mock_ai)
        await describer.run()
        mock_gh.publish_persistent_comment.assert_called_once()
