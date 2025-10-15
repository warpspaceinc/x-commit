"""Message parser for extracting GitHub commit information from Slack messages."""

import logging
import re
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ParsedCommit:
    """Parsed commit information from a message."""

    owner: str
    repo: str
    sha: str
    commit_url: str
    branch: Optional[str] = None
    author: Optional[str] = None
    message: Optional[str] = None


class MessageParser:
    """Parser for extracting GitHub commit information from various message formats."""

    # GitHub commit URL pattern
    COMMIT_URL_PATTERN = re.compile(
        r"github\.com/(?P<owner>[^/\s]+)/(?P<repo>[^/\s]+)/commit/(?P<sha>[a-f0-9]{7,40})",
        re.IGNORECASE
    )

    # GitHub Slack app format: "user pushed to branch: url - message"
    GITHUB_SLACK_FORMAT = re.compile(
        r"(?P<author>\S+)\s+pushed\s+to\s+(?P<branch>\S+):\s+"
        r"(?P<url>https?://github\.com/[^/]+/[^/]+/commit/[a-f0-9]+)"
        r"(?:\s+-\s+(?P<message>.+))?",
        re.IGNORECASE
    )

    # GitHub Slack app new format: "1 new commit pushed to _branch_ by author"
    GITHUB_SLACK_NEW_FORMAT = re.compile(
        r"pushed\s+to\s+[_*]?(?P<branch>[^_*\s]+)[_*]?\s+by\s+(?P<author>\S+)",
        re.IGNORECASE
    )

    # Markdown link format: [text](url)
    MARKDOWN_LINK_PATTERN = re.compile(
        r"\[([^\]]+)\]\((?P<url>https?://github\.com/[^/]+/[^/]+/commit/[a-f0-9]+)\)",
        re.IGNORECASE
    )

    # Slack link format: <url|text> or <url>
    SLACK_LINK_PATTERN = re.compile(
        r"<(?P<url>https?://github\.com/[^/|>]+/[^/|>]+/commit/[a-f0-9]+)(?:\|[^>]+)?>",
        re.IGNORECASE
    )

    def parse_message(self, message: str) -> Optional[ParsedCommit]:
        """Parse a message to extract GitHub commit information.

        Supports multiple formats:
        1. GitHub Slack app format: "user pushed to branch: url - message"
        2. Direct commit URL: https://github.com/owner/repo/commit/sha
        3. Markdown link: [text](url)
        4. Slack link: <url|text> or <url>

        Args:
            message: The message text to parse

        Returns:
            ParsedCommit object if successful, None otherwise
        """
        if not message or not isinstance(message, str):
            return None

        # Try GitHub Slack app format first (most structured)
        parsed = self._parse_github_slack_format(message)
        if parsed:
            return parsed

        # Try Slack link format
        parsed = self._parse_slack_link_format(message)
        if parsed:
            return parsed

        # Try Markdown link format
        parsed = self._parse_markdown_link_format(message)
        if parsed:
            return parsed

        # Try direct URL extraction
        parsed = self._parse_direct_url(message)
        if parsed:
            return parsed

        logger.debug(f"No GitHub commit URL found in message: {message[:100]}")
        return None

    def _parse_github_slack_format(self, message: str) -> Optional[ParsedCommit]:
        """Parse GitHub Slack app notification format.

        Format: "user pushed to branch: url - message"
        Example: "rick pushed to main: https://github.com/owner/repo/commit/abc123 - Update README"
        """
        match = self.GITHUB_SLACK_FORMAT.search(message)
        if not match:
            return None

        url = match.group("url")
        commit_info = self._extract_url_components(url)

        if not commit_info:
            return None

        return ParsedCommit(
            owner=commit_info["owner"],
            repo=commit_info["repo"],
            sha=commit_info["sha"],
            commit_url=url,
            branch=match.group("branch"),
            author=match.group("author"),
            message=match.group("message"),
        )

    def _parse_slack_link_format(self, message: str) -> Optional[ParsedCommit]:
        """Parse Slack link format.

        Format: <url|text> or <url>
        Example: <https://github.com/owner/repo/commit/abc123|View commit>
        """
        match = self.SLACK_LINK_PATTERN.search(message)
        if not match:
            return None

        url = match.group("url")
        commit_info = self._extract_url_components(url)

        if not commit_info:
            return None

        return ParsedCommit(
            owner=commit_info["owner"],
            repo=commit_info["repo"],
            sha=commit_info["sha"],
            commit_url=url,
        )

    def _parse_markdown_link_format(self, message: str) -> Optional[ParsedCommit]:
        """Parse Markdown link format.

        Format: [text](url)
        Example: [View commit](https://github.com/owner/repo/commit/abc123)
        """
        match = self.MARKDOWN_LINK_PATTERN.search(message)
        if not match:
            return None

        url = match.group("url")
        commit_info = self._extract_url_components(url)

        if not commit_info:
            return None

        return ParsedCommit(
            owner=commit_info["owner"],
            repo=commit_info["repo"],
            sha=commit_info["sha"],
            commit_url=url,
        )

    def _parse_direct_url(self, message: str) -> Optional[ParsedCommit]:
        """Parse direct GitHub commit URL.

        Format: https://github.com/owner/repo/commit/sha
        """
        match = self.COMMIT_URL_PATTERN.search(message)
        if not match:
            return None

        owner = match.group("owner")
        repo = match.group("repo")
        sha = match.group("sha")

        # Reconstruct the full URL
        commit_url = f"https://github.com/{owner}/{repo}/commit/{sha}"

        return ParsedCommit(
            owner=owner,
            repo=repo,
            sha=sha,
            commit_url=commit_url,
        )

    def _extract_url_components(self, url: str) -> Optional[dict]:
        """Extract owner, repo, and sha from a GitHub commit URL."""
        match = self.COMMIT_URL_PATTERN.search(url)
        if not match:
            return None

        return {
            "owner": match.group("owner"),
            "repo": match.group("repo"),
            "sha": match.group("sha"),
        }

    def is_github_commit_message(self, message: str, bot_id: Optional[str] = None) -> bool:
        """Check if a message contains a GitHub commit reference.

        Args:
            message: The message text to check
            bot_id: Optional bot ID to verify the message is from GitHub app

        Returns:
            True if the message contains a GitHub commit URL
        """
        if not message:
            return False

        # Check if message contains a commit URL
        return self.COMMIT_URL_PATTERN.search(message) is not None

    def extract_all_commits(self, message: str) -> list[ParsedCommit]:
        """Extract all commit references from a message.

        Useful for messages that mention multiple commits.

        Args:
            message: The message text to parse

        Returns:
            List of ParsedCommit objects
        """
        commits = []
        seen_shas = set()

        # Extract branch and author from new GitHub Slack format
        branch_info = None
        new_format_match = self.GITHUB_SLACK_NEW_FORMAT.search(message)
        if new_format_match:
            branch_info = {
                "branch": new_format_match.group("branch"),
                "author": new_format_match.group("author"),
            }

        # First try to parse GitHub Slack app format (includes branch info)
        for match in self.GITHUB_SLACK_FORMAT.finditer(message):
            url = match.group("url")
            commit_info = self._extract_url_components(url)

            if not commit_info:
                continue

            sha = commit_info["sha"]

            # Avoid duplicates
            if sha in seen_shas:
                continue

            seen_shas.add(sha)

            commits.append(
                ParsedCommit(
                    owner=commit_info["owner"],
                    repo=commit_info["repo"],
                    sha=sha,
                    commit_url=url,
                    branch=match.group("branch"),
                    author=match.group("author"),
                    message=match.group("message"),
                )
            )

        # Then find any remaining commit URLs and apply branch info from new format
        for match in self.COMMIT_URL_PATTERN.finditer(message):
            owner = match.group("owner")
            repo = match.group("repo")
            sha = match.group("sha")

            # Avoid duplicates
            if sha in seen_shas:
                continue

            seen_shas.add(sha)
            commit_url = f"https://github.com/{owner}/{repo}/commit/{sha}"

            # Apply branch info from new format if available
            commits.append(
                ParsedCommit(
                    owner=owner,
                    repo=repo,
                    sha=sha,
                    commit_url=commit_url,
                    branch=branch_info["branch"] if branch_info else None,
                    author=branch_info["author"] if branch_info else None,
                )
            )

        return commits


# Convenience function
def parse_commit_from_message(message: str) -> Optional[ParsedCommit]:
    """Parse a message and extract GitHub commit information.

    This is a convenience function that creates a MessageParser
    and calls parse_message().

    Args:
        message: The message text to parse

    Returns:
        ParsedCommit object if successful, None otherwise
    """
    parser = MessageParser()
    return parser.parse_message(message)
