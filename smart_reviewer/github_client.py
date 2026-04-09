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
            ``https://github.com/owner/repo/pull/42`` or a GitHub Enterprise
            URL like ``https://github.example.com/owner/repo/pull/42``.
        api_url: Optional GitHub API base URL for GitHub Enterprise Server.
            For example ``https://github.example.com/api/v3``.  When empty
            the client auto-detects: if *pr_url* points at ``github.com`` the
            public API is used, otherwise ``https://<host>/api/v3`` is assumed.
        ssl_verify: Whether to verify SSL certificates.  Set to ``False`` when
            behind a corporate proxy with custom CA certificates.
    """

    _URL_PATTERN = re.compile(
        r"https?://(?P<host>[^/]+)/(?P<owner>[^/]+)/(?P<repo>[^/]+)/pull/(?P<number>\d+)"
    )

    def __init__(
        self,
        token: str,
        pr_url: str,
        api_url: str = "",
        ssl_verify: bool = True,
    ) -> None:
        self.token = token
        self.pr_url = pr_url

        match = self._URL_PATTERN.match(pr_url)
        if not match:
            raise ValueError(f"Invalid PR URL: {pr_url}")

        self.host = match.group("host")
        self.owner = match.group("owner")
        self.repo_name = match.group("repo")
        self.pr_number = int(match.group("number"))

        # Determine the GitHub API endpoint.
        if api_url:
            base_url = api_url.rstrip("/")
        elif self.host.lower() in ("github.com", "www.github.com"):
            base_url = ""  # use PyGithub default (https://api.github.com)
        else:
            # GitHub Enterprise Server convention
            base_url = f"https://{self.host}/api/v3"

        kwargs: dict[str, Any] = {}
        if base_url:
            kwargs["base_url"] = base_url
        if not ssl_verify:
            kwargs["verify"] = False

        self._github = Github(token, **kwargs)
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

    def get_past_reviews(self) -> list[dict[str, Any]]:
        """Return past reviews with their inline comment threads.

        Each entry represents a submitted review and includes:
        - ``reviewer``: GitHub login of the reviewer.
        - ``state``: Review state (e.g. ``APPROVED``, ``CHANGES_REQUESTED``).
        - ``body``: Top-level review body (may be empty).
        - ``submitted_at``: ISO-formatted timestamp.
        - ``comments``: List of inline review comments belonging to this
          review, each with ``path``, ``body``, ``diff_hunk``, ``line``,
          and ``in_reply_to_id``.
        """
        reviews: list[dict[str, Any]] = []
        # Build a lookup of review comments grouped by review id
        review_comments_by_id: dict[int, list[dict[str, Any]]] = {}
        for rc in self._pr.get_review_comments():
            rid = rc.pull_request_review_id
            if rid is None:
                continue
            comment_data = {
                "path": rc.path,
                "body": rc.body,
                "diff_hunk": rc.diff_hunk,
                "line": getattr(rc, "line", None),
                "in_reply_to_id": getattr(rc, "in_reply_to_id", None),
            }
            review_comments_by_id.setdefault(rid, []).append(comment_data)

        for review in self._pr.get_reviews():
            reviews.append(
                {
                    "reviewer": review.user.login if review.user else "unknown",
                    "state": review.state,
                    "body": review.body or "",
                    "submitted_at": (
                        review.submitted_at.isoformat()
                        if review.submitted_at
                        else ""
                    ),
                    "comments": review_comments_by_id.get(review.id, []),
                }
            )

        return reviews

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
