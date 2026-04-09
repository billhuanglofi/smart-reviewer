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
            assert match.group("host") == "github.com"
            assert match.group("owner") == "owner"
            assert match.group("repo") == "repo"
            assert match.group("number") == "42"

    def test_github_enterprise_url(self):
        with mock.patch("smart_reviewer.github_client.Github"):
            client = GitHubClient.__new__(GitHubClient)
            match = client._URL_PATTERN.match(
                "https://github.example.com/myorg/myrepo/pull/99"
            )
            assert match is not None
            assert match.group("host") == "github.example.com"
            assert match.group("owner") == "myorg"
            assert match.group("repo") == "myrepo"
            assert match.group("number") == "99"

    def test_invalid_url(self):
        with mock.patch("smart_reviewer.github_client.Github"):
            with pytest.raises(ValueError, match="Invalid PR URL"):
                GitHubClient("tok", "https://not-a-pr-url/foo")


# ---------------------------------------------------------------------------
# GitHub Enterprise / custom API URL construction
# ---------------------------------------------------------------------------

class TestGitHubEnterprise:
    def test_public_github_uses_default_api(self):
        """github.com URLs should not pass base_url to PyGithub."""
        with mock.patch("smart_reviewer.github_client.Github") as MockGithub:
            mock_github_instance = MockGithub.return_value
            mock_repo = mock.MagicMock()
            mock_github_instance.get_repo.return_value = mock_repo
            mock_repo.get_pull.return_value = mock.MagicMock()
            GitHubClient("tok", "https://github.com/owner/repo/pull/1")
            # Should be called with just the token (no base_url)
            MockGithub.assert_called_once_with("tok")

    def test_ghe_auto_detects_api_url(self):
        """Non-github.com hosts should auto-detect the GHE API URL."""
        with mock.patch("smart_reviewer.github_client.Github") as MockGithub:
            mock_github_instance = MockGithub.return_value
            mock_repo = mock.MagicMock()
            mock_github_instance.get_repo.return_value = mock_repo
            mock_repo.get_pull.return_value = mock.MagicMock()
            GitHubClient(
                "tok",
                "https://github.example.com/myorg/myrepo/pull/5",
            )
            MockGithub.assert_called_once_with(
                "tok", base_url="https://github.example.com/api/v3"
            )

    def test_explicit_api_url_overrides(self):
        """An explicit api_url should be used even for github.com."""
        with mock.patch("smart_reviewer.github_client.Github") as MockGithub:
            mock_github_instance = MockGithub.return_value
            mock_repo = mock.MagicMock()
            mock_github_instance.get_repo.return_value = mock_repo
            mock_repo.get_pull.return_value = mock.MagicMock()
            GitHubClient(
                "tok",
                "https://github.com/owner/repo/pull/1",
                api_url="https://custom-proxy.corp.com/github/api/v3",
            )
            MockGithub.assert_called_once_with(
                "tok",
                base_url="https://custom-proxy.corp.com/github/api/v3",
            )

    def test_ssl_verify_false_passed(self):
        """ssl_verify=False should be forwarded to PyGithub."""
        with mock.patch("smart_reviewer.github_client.Github") as MockGithub:
            mock_github_instance = MockGithub.return_value
            mock_repo = mock.MagicMock()
            mock_github_instance.get_repo.return_value = mock_repo
            mock_repo.get_pull.return_value = mock.MagicMock()
            GitHubClient(
                "tok",
                "https://github.com/owner/repo/pull/1",
                ssl_verify=False,
            )
            MockGithub.assert_called_once_with("tok", verify=False)


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
# Past reviews
# ---------------------------------------------------------------------------

class TestGetPastReviews:
    def test_returns_reviews_with_comments(self):
        client, mock_pr = _make_client()

        # Set up a review
        review = mock.MagicMock()
        review.id = 101
        review.user.login = "bob"
        review.state = "CHANGES_REQUESTED"
        review.body = "Please fix the typo."
        review.submitted_at = datetime(2025, 3, 15, 10, 0, 0)
        mock_pr.get_reviews.return_value = [review]

        # Set up review comments linked to that review
        rc = mock.MagicMock()
        rc.pull_request_review_id = 101
        rc.path = "src/main.py"
        rc.body = "Typo on this line"
        rc.diff_hunk = "@@ -1,3 +1,3 @@"
        rc.line = 5
        rc.in_reply_to_id = None
        mock_pr.get_review_comments.return_value = [rc]

        reviews = client.get_past_reviews()
        assert len(reviews) == 1
        assert reviews[0]["reviewer"] == "bob"
        assert reviews[0]["state"] == "CHANGES_REQUESTED"
        assert reviews[0]["body"] == "Please fix the typo."
        assert "2025-03-15" in reviews[0]["submitted_at"]
        assert len(reviews[0]["comments"]) == 1
        assert reviews[0]["comments"][0]["path"] == "src/main.py"
        assert reviews[0]["comments"][0]["body"] == "Typo on this line"

    def test_review_without_comments(self):
        client, mock_pr = _make_client()

        review = mock.MagicMock()
        review.id = 200
        review.user.login = "alice"
        review.state = "APPROVED"
        review.body = "LGTM"
        review.submitted_at = datetime(2025, 4, 1)
        mock_pr.get_reviews.return_value = [review]
        mock_pr.get_review_comments.return_value = []

        reviews = client.get_past_reviews()
        assert len(reviews) == 1
        assert reviews[0]["reviewer"] == "alice"
        assert reviews[0]["state"] == "APPROVED"
        assert reviews[0]["comments"] == []

    def test_empty_reviews(self):
        client, mock_pr = _make_client()
        mock_pr.get_reviews.return_value = []
        mock_pr.get_review_comments.return_value = []

        reviews = client.get_past_reviews()
        assert reviews == []

    def test_comment_without_review_id_skipped(self):
        client, mock_pr = _make_client()

        review = mock.MagicMock()
        review.id = 300
        review.user.login = "carol"
        review.state = "COMMENTED"
        review.body = ""
        review.submitted_at = None
        mock_pr.get_reviews.return_value = [review]

        # Comment with no review id should be skipped
        rc = mock.MagicMock()
        rc.pull_request_review_id = None
        rc.path = "README.md"
        rc.body = "orphan comment"
        rc.diff_hunk = ""
        rc.line = None
        rc.in_reply_to_id = None
        mock_pr.get_review_comments.return_value = [rc]

        reviews = client.get_past_reviews()
        assert len(reviews) == 1
        assert reviews[0]["comments"] == []
        assert reviews[0]["submitted_at"] == ""

    def test_multiple_reviews_multiple_comments(self):
        client, mock_pr = _make_client()

        r1 = mock.MagicMock()
        r1.id = 10
        r1.user.login = "alice"
        r1.state = "COMMENTED"
        r1.body = ""
        r1.submitted_at = datetime(2025, 1, 1)

        r2 = mock.MagicMock()
        r2.id = 20
        r2.user.login = "bob"
        r2.state = "CHANGES_REQUESTED"
        r2.body = "Needs work"
        r2.submitted_at = datetime(2025, 1, 2)

        mock_pr.get_reviews.return_value = [r1, r2]

        rc1 = mock.MagicMock()
        rc1.pull_request_review_id = 10
        rc1.path = "a.py"
        rc1.body = "nit"
        rc1.diff_hunk = "@@"
        rc1.line = 1
        rc1.in_reply_to_id = None

        rc2 = mock.MagicMock()
        rc2.pull_request_review_id = 20
        rc2.path = "b.py"
        rc2.body = "bug here"
        rc2.diff_hunk = "@@"
        rc2.line = 10
        rc2.in_reply_to_id = None

        rc3 = mock.MagicMock()
        rc3.pull_request_review_id = 20
        rc3.path = "b.py"
        rc3.body = "also here"
        rc3.diff_hunk = "@@"
        rc3.line = 15
        rc3.in_reply_to_id = None

        mock_pr.get_review_comments.return_value = [rc1, rc2, rc3]

        reviews = client.get_past_reviews()
        assert len(reviews) == 2
        assert len(reviews[0]["comments"]) == 1
        assert len(reviews[1]["comments"]) == 2


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
