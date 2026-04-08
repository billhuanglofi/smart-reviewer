"""GitHub client for fetching PR data and posting comments."""

from __future__ import annotations

import logging
import re
from typing import Any

from github import Github

logger = logging.getLogger(__name__)


class GitHubClient:
    """Wrapper around PyGithub for PR interactions.

    Parameters:
        token: GitHub personal access token or ``GITHUB_TOKEN``.
        pr_url: Full URL to the pull request, e.g.
            ``https://github.com/owner/repo/pull/42``.
    """

    _URL_PATTERN = re.compile(
        r"https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/pull/(?P<number>\d+)"
    )

    def __init__(self, token: str, pr_url: str) -> None:
        self.token = token
        self.pr_url = pr_url

        match = self._URL_PATTERN.match(pr_url)
        if not match:
            raise ValueError(f"Invalid PR URL: {pr_url}")

        self.owner = match.group("owner")
        self.repo_name = match.group("repo")
        self.pr_number = int(match.group("number"))

        self._github = Github(token)
        self._repo = self._github.get_repo(f"{self.owner}/{self.repo_name}")
        self._pr = self._repo.get_pull(self.pr_number)

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------

    def get_pr_info(self) -> dict[str, Any]:
        """Return basic PR metadata."""
        pr = self._pr
        return {
            "title": pr.title,
            "body": pr.body or "",
            "branch": pr.head.ref,
            "base_branch": pr.base.ref,
            "author": pr.user.login,
            "created_at": pr.created_at.isoformat(),
        }

    def get_pr_diff(self) -> str:
        """Return the unified diff of the PR as a string."""
        # PyGithub doesn't expose diff directly; we fetch via the API.
        headers, data = self._repo._requester.requestJsonAndCheck(
            "GET",
            self._pr.url,
            headers={"Accept": "application/vnd.github.v3.diff"},
        )
        return data if isinstance(data, str) else ""

    def get_pr_files(self) -> list[dict[str, Any]]:
        """Return a list of changed files with patch info."""
        files: list[dict[str, Any]] = []
        for f in self._pr.get_files():
            files.append(
                {
                    "filename": f.filename,
                    "status": f.status,
                    "additions": f.additions,
                    "deletions": f.deletions,
                    "patch": getattr(f, "patch", None) or "",
                }
            )
        return files

    def get_commit_messages(self) -> str:
        """Return newline-separated commit messages."""
        commits = self._pr.get_commits()
        return "\n".join(c.commit.message for c in commits)

    def get_languages(self) -> dict[str, int]:
        """Return the language breakdown of the repository."""
        return self._repo.get_languages()

    # ------------------------------------------------------------------
    # Write helpers
    # ------------------------------------------------------------------

    def publish_comment(self, body: str) -> None:
        """Post a new comment on the PR."""
        self._pr.create_issue_comment(body)
        logger.info("Published comment on PR #%d", self.pr_number)

    def publish_persistent_comment(self, body: str, header: str) -> None:
        """Edit an existing comment that starts with *header*, or create one.

        This ensures that repeated runs update the same comment instead of
        creating duplicates.
        """
        full_body = f"{header}\n\n{body}"
        for comment in self._pr.get_issue_comments():
            if comment.body.startswith(header):
                comment.edit(full_body)
                logger.info(
                    "Updated existing comment on PR #%d", self.pr_number
                )
                return

        self._pr.create_issue_comment(full_body)
        logger.info("Created new persistent comment on PR #%d", self.pr_number)
