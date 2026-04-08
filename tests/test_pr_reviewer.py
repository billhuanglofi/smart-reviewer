"""Tests for PRReviewer tool."""

from __future__ import annotations

from unittest import mock

import pytest

from smart_reviewer.config import ReviewConfig
from smart_reviewer.tools.pr_reviewer import PRReviewer, _format_markdown, _parse_yaml

SAMPLE_YAML = """\
estimated_effort_to_review: 3
key_issues_to_review:
  - relevant_file: "src/main.py"
    issue_header: "Null check missing"
    issue_content: "The variable may be None."
    start_line: 10
    end_line: 12
security_concerns: "SQL injection risk in query builder"
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
        assert data["estimated_effort_to_review"] == 3
        assert len(data["key_issues_to_review"]) == 1

    def test_yaml_with_fences(self):
        fenced = f"```yaml\n{SAMPLE_YAML}\n```"
        data = _parse_yaml(fenced)
        assert data["estimated_effort_to_review"] == 3

    def test_malformed_yaml(self):
        data = _parse_yaml("not: [valid: yaml: {{{")
        assert data == {}

    def test_non_dict_yaml(self):
        data = _parse_yaml("- item1\n- item2")
        assert data == {}


class TestFormatMarkdown:
    def test_includes_effort_badge(self):
        data = {"estimated_effort_to_review": 3}
        config = _make_config(require_effort_estimation=True)
        md = _format_markdown(data, config)
        assert "Moderate (3/5)" in md

    def test_includes_issues_table(self):
        data = _parse_yaml(SAMPLE_YAML)
        config = _make_config()
        md = _format_markdown(data, config)
        assert "src/main.py" in md
        assert "Null check missing" in md

    def test_no_issues(self):
        data = {"key_issues_to_review": []}
        config = _make_config()
        md = _format_markdown(data, config)
        assert "No critical issues" in md

    def test_security_section(self):
        data = {"security_concerns": "XSS vulnerability"}
        config = _make_config(require_security_review=True)
        md = _format_markdown(data, config)
        assert "XSS vulnerability" in md

    def test_no_security_concerns(self):
        data = {"security_concerns": ""}
        config = _make_config(require_security_review=True)
        md = _format_markdown(data, config)
        assert "No security concerns" in md


class TestPRReviewerRun:
    @pytest.mark.asyncio
    async def test_full_flow(self):
        config = _make_config(publish_output=False)
        mock_gh = mock.MagicMock()
        mock_gh.get_pr_info.return_value = {
            "title": "Test PR",
            "body": "Description",
            "branch": "feature",
            "base_branch": "main",
            "author": "alice",
            "created_at": "2025-01-01T00:00:00",
        }
        mock_gh.get_pr_diff.return_value = "diff content"
        mock_gh.get_pr_files.return_value = []

        mock_ai = mock.MagicMock()
        mock_ai.chat_completion = mock.AsyncMock(return_value=SAMPLE_YAML)

        reviewer = PRReviewer(config, mock_gh, mock_ai)
        result = await reviewer.run()

        assert "Null check missing" in result
        assert "SQL injection" in result
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
        mock_gh.get_pr_files.return_value = []

        mock_ai = mock.MagicMock()
        mock_ai.chat_completion = mock.AsyncMock(return_value=SAMPLE_YAML)

        reviewer = PRReviewer(config, mock_gh, mock_ai)
        await reviewer.run()

        mock_gh.publish_persistent_comment.assert_called_once()
