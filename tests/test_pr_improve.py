"""Tests for PRImprove tool."""

from __future__ import annotations

from unittest import mock

import pytest

from smart_reviewer.config import ReviewConfig
from smart_reviewer.tools.pr_improve import PRImprove, _format_markdown, _parse_yaml

SAMPLE_YAML = """\
code_suggestions:
  - relevant_file: "src/utils.py"
    suggestion_header: "Use list comprehension"
    suggestion_content: "Replace manual loop with a list comprehension for clarity."
    existing_code: |
      result = []
      for item in items:
          result.append(item.upper())
    improved_code: |
      result = [item.upper() for item in items]
    start_line: 15
    end_line: 18
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
        assert len(data["code_suggestions"]) == 1

    def test_yaml_with_fences(self):
        fenced = f"```yaml\n{SAMPLE_YAML}\n```"
        data = _parse_yaml(fenced)
        assert "code_suggestions" in data

    def test_malformed_yaml(self):
        assert _parse_yaml("{{{bad") == {}

    def test_non_dict_yaml(self):
        assert _parse_yaml("- a") == {}


class TestFormatMarkdown:
    def test_includes_suggestion(self):
        data = _parse_yaml(SAMPLE_YAML)
        md = _format_markdown(data)
        assert "Use list comprehension" in md
        assert "src/utils.py" in md

    def test_includes_code_blocks(self):
        data = _parse_yaml(SAMPLE_YAML)
        md = _format_markdown(data)
        assert "Existing code" in md
        assert "Improved code" in md

    def test_no_suggestions(self):
        data = {"code_suggestions": []}
        md = _format_markdown(data)
        assert "No improvement suggestions" in md

    def test_empty_data(self):
        md = _format_markdown({})
        assert "No improvement suggestions" in md


class TestPRImproveRun:
    @pytest.mark.asyncio
    async def test_full_flow(self):
        config = _make_config(publish_output=False)
        mock_gh = mock.MagicMock()
        mock_gh.get_pr_info.return_value = {
            "title": "Refactor utils",
            "body": "Clean up",
            "branch": "refactor",
            "base_branch": "main",
            "author": "carol",
            "created_at": "2025-01-01",
        }
        mock_gh.get_pr_diff.return_value = "diff"

        mock_ai = mock.MagicMock()
        mock_ai.chat_completion = mock.AsyncMock(return_value=SAMPLE_YAML)

        improver = PRImprove(config, mock_gh, mock_ai)
        result = await improver.run()

        assert "Use list comprehension" in result
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

        mock_ai = mock.MagicMock()
        mock_ai.chat_completion = mock.AsyncMock(return_value=SAMPLE_YAML)

        improver = PRImprove(config, mock_gh, mock_ai)
        await improver.run()
        mock_gh.publish_persistent_comment.assert_called_once()
