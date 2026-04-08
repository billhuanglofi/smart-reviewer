"""Tests for GitHubClient."""

from __future__ import annotations

from datetime import datetime
from unittest import mock

import pytest

from smart_reviewer.github_client import GitHubClient


# ---------------------------------------------------------------------------
# URL parsing
# ---------------------------------------------------------------------------

class TestURLParsing:
    def test_valid_url(self):
        with mock.patch("smart_reviewer.github_client.Github"):
            client = GitHubClient.__new__(GitHubClient)
            match = client._URL_PATTERN.match(
                "https://github.com/owner/repo/pull/42"
            )
            assert match is not None
            assert match.group("owner") == "owner"
            assert match.group("repo") == "repo"
            assert match.group("number") == "42"

    def test_invalid_url(self):
        with mock.patch("smart_reviewer.github_client.Github"):
            with pytest.raises(ValueError, match="Invalid PR URL"):
                GitHubClient("tok", "https://not-github.com/foo/bar")


# ---------------------------------------------------------------------------
# Helper to build a fully-mocked client
# ---------------------------------------------------------------------------

def _make_client() -> tuple[GitHubClient, mock.MagicMock]:
    """Return a GitHubClient with a fully mocked Github backend."""
    with mock.patch("smart_reviewer.github_client.Github") as MockGithub:
        mock_github_instance = MockGithub.return_value
        mock_repo = mock.MagicMock()
        mock_github_instance.get_repo.return_value = mock_repo
        mock_pr = mock.MagicMock()
        mock_repo.get_pull.return_value = mock_pr
        client = GitHubClient("tok", "https://github.com/owner/repo/pull/7")
    return client, mock_pr


# ---------------------------------------------------------------------------
# Read helpers
# ---------------------------------------------------------------------------

class TestGetPRInfo:
    def test_returns_expected_keys(self):
        client, mock_pr = _make_client()
        mock_pr.title = "Fix bug"
        mock_pr.body = "Fixes #1"
        mock_pr.head.ref = "feature"
        mock_pr.base.ref = "main"
        mock_pr.user.login = "alice"
        mock_pr.created_at = datetime(2025, 1, 1, 12, 0, 0)

        info = client.get_pr_info()
        assert info["title"] == "Fix bug"
        assert info["body"] == "Fixes #1"
        assert info["branch"] == "feature"
        assert info["base_branch"] == "main"
        assert info["author"] == "alice"
        assert "2025-01-01" in info["created_at"]

    def test_none_body_becomes_empty(self):
        client, mock_pr = _make_client()
        mock_pr.body = None
        mock_pr.title = "t"
        mock_pr.head.ref = "b"
        mock_pr.base.ref = "m"
        mock_pr.user.login = "u"
        mock_pr.created_at = datetime(2025, 1, 1)
        assert client.get_pr_info()["body"] == ""


class TestGetPRFiles:
    def test_returns_list_of_dicts(self):
        client, mock_pr = _make_client()
        mock_file = mock.MagicMock()
        mock_file.filename = "src/main.py"
        mock_file.status = "modified"
        mock_file.additions = 10
        mock_file.deletions = 2
        mock_file.patch = "@@ diff @@"
        mock_pr.get_files.return_value = [mock_file]

        files = client.get_pr_files()
        assert len(files) == 1
        assert files[0]["filename"] == "src/main.py"
        assert files[0]["additions"] == 10


class TestGetCommitMessages:
    def test_joins_messages(self):
        client, mock_pr = _make_client()
        c1 = mock.MagicMock()
        c1.commit.message = "first commit"
        c2 = mock.MagicMock()
        c2.commit.message = "second commit"
        mock_pr.get_commits.return_value = [c1, c2]

        result = client.get_commit_messages()
        assert "first commit" in result
        assert "second commit" in result


class TestGetLanguages:
    def test_returns_dict(self):
        client, _ = _make_client()
        client._repo.get_languages.return_value = {"Python": 1000}
        assert client.get_languages() == {"Python": 1000}


# ---------------------------------------------------------------------------
# Write helpers
# ---------------------------------------------------------------------------

class TestPublishComment:
    def test_creates_comment(self):
        client, mock_pr = _make_client()
        client.publish_comment("hello")
        mock_pr.create_issue_comment.assert_called_once_with("hello")


class TestPublishPersistentComment:
    def test_updates_existing(self):
        client, mock_pr = _make_client()
        existing = mock.MagicMock()
        existing.body = "## Header\n\nold body"
        mock_pr.get_issue_comments.return_value = [existing]

        client.publish_persistent_comment("new body", "## Header")
        existing.edit.assert_called_once()
        mock_pr.create_issue_comment.assert_not_called()

    def test_creates_new_when_no_match(self):
        client, mock_pr = _make_client()
        mock_pr.get_issue_comments.return_value = []
        client.publish_persistent_comment("body", "## Header")
        mock_pr.create_issue_comment.assert_called_once()
