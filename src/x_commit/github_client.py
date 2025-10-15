"""GitHub API client for fetching commit information."""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from github import Github, GithubException
from github.Commit import Commit
from github.Repository import Repository

from .config import get_config

logger = logging.getLogger(__name__)


@dataclass
class CommitInfo:
    """Structured commit information."""

    sha: str
    message: str
    author_name: str
    author_email: str
    date: datetime
    repository: str
    url: str
    files_changed: int
    additions: int
    deletions: int


@dataclass
class FileChange:
    """Information about a changed file in a commit."""

    filename: str
    status: str  # added, removed, modified, renamed
    additions: int
    deletions: int
    changes: int
    patch: Optional[str] = None


class GitHubClient:
    """Client for interacting with GitHub API."""

    def __init__(self, token: Optional[str] = None):
        """Initialize GitHub client.

        Args:
            token: GitHub personal access token. If not provided, uses config.
        """
        config = get_config()
        self.token = token or config.github_token
        self.client = Github(self.token)
        logger.info("GitHub client initialized")

    def parse_commit_url(self, url: str) -> tuple[str, str, str]:
        """Parse GitHub commit URL to extract owner, repo, and commit SHA.

        Args:
            url: GitHub commit URL (e.g., https://github.com/owner/repo/commit/sha)

        Returns:
            Tuple of (owner, repo, sha)

        Raises:
            ValueError: If URL format is invalid
        """
        parts = url.rstrip("/").split("/")

        try:
            if "github.com" in url:
                # Find the github.com part
                gh_index = next(i for i, p in enumerate(parts) if "github.com" in p)
                owner = parts[gh_index + 1]
                repo = parts[gh_index + 2]
                # commit should be at gh_index + 3
                if parts[gh_index + 3] == "commit":
                    sha = parts[gh_index + 4]
                else:
                    raise ValueError("Invalid commit URL format")
                return owner, repo, sha
            else:
                raise ValueError("Not a GitHub URL")
        except (IndexError, StopIteration, ValueError) as e:
            raise ValueError(
                f"Invalid GitHub commit URL: {url}. "
                "Expected format: https://github.com/owner/repo/commit/sha"
            ) from e

    def get_commit(
        self, owner: str, repo: str, sha: str
    ) -> tuple[CommitInfo, List[FileChange]]:
        """Fetch commit information from GitHub.

        Args:
            owner: Repository owner
            repo: Repository name
            sha: Commit SHA

        Returns:
            Tuple of (CommitInfo, List[FileChange])

        Raises:
            GithubException: If commit cannot be fetched
        """
        try:
            logger.info(f"Fetching commit {sha} from {owner}/{repo}")
            repository = self.client.get_repo(f"{owner}/{repo}")
            commit = repository.get_commit(sha)

            commit_info = self._extract_commit_info(commit, repository)
            file_changes = self._extract_file_changes(commit)

            logger.info(
                f"Successfully fetched commit: {len(file_changes)} files changed"
            )
            return commit_info, file_changes

        except GithubException as e:
            logger.error(f"Failed to fetch commit: {e}")
            raise

    def get_commit_by_url(self, url: str) -> tuple[CommitInfo, List[FileChange]]:
        """Fetch commit information using a GitHub URL.

        Args:
            url: GitHub commit URL

        Returns:
            Tuple of (CommitInfo, List[FileChange])
        """
        owner, repo, sha = self.parse_commit_url(url)
        return self.get_commit(owner, repo, sha)

    def _extract_commit_info(self, commit: Commit, repo: Repository) -> CommitInfo:
        """Extract structured information from a GitHub commit."""
        # Convert PaginatedList to list to get length
        files_list = list(commit.files)

        return CommitInfo(
            sha=commit.sha,
            message=commit.commit.message,
            author_name=commit.commit.author.name,
            author_email=commit.commit.author.email,
            date=commit.commit.author.date,
            repository=repo.full_name,
            url=commit.html_url,
            files_changed=len(files_list),
            additions=commit.stats.additions,
            deletions=commit.stats.deletions,
        )

    def _extract_file_changes(self, commit: Commit) -> List[FileChange]:
        """Extract file changes from a commit."""
        file_changes = []

        for file in commit.files:
            file_change = FileChange(
                filename=file.filename,
                status=file.status,
                additions=file.additions,
                deletions=file.deletions,
                changes=file.changes,
                patch=file.patch if hasattr(file, "patch") else None,
            )
            file_changes.append(file_change)

        return file_changes

    def format_diff(
        self, file_changes: List[FileChange], max_lines: Optional[int] = None
    ) -> str:
        """Format file changes into a readable diff string.

        Args:
            file_changes: List of file changes
            max_lines: Maximum number of lines to include (None for unlimited)

        Returns:
            Formatted diff string
        """
        config = get_config()
        if max_lines is None:
            max_lines = config.max_diff_lines

        diff_parts = []
        total_lines = 0
        truncated = False

        for change in file_changes:
            header = f"\n{'='*60}\nFile: {change.filename} ({change.status})\n"
            header += f"+{change.additions} -{change.deletions} (~{change.changes} changes)\n"
            header += f"{'='*60}\n"

            diff_parts.append(header)
            total_lines += header.count("\n")

            if change.patch:
                patch_lines = change.patch.split("\n")
                remaining_lines = max_lines - total_lines

                if remaining_lines <= 0:
                    truncated = True
                    break

                if len(patch_lines) > remaining_lines:
                    diff_parts.append("\n".join(patch_lines[:remaining_lines]))
                    diff_parts.append(
                        f"\n... (truncated {len(patch_lines) - remaining_lines} lines)"
                    )
                    truncated = True
                    break
                else:
                    diff_parts.append(change.patch)
                    total_lines += len(patch_lines)
            else:
                diff_parts.append("(Binary file or no diff available)\n")
                total_lines += 1

        result = "\n".join(diff_parts)

        if truncated:
            result += f"\n\n⚠️  Diff truncated at {max_lines} lines to limit size."

        return result
