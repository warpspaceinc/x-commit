"""Core analyzer engine that coordinates GitHub and Claude clients."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from .claude_client import ClaudeClient
from .config import get_config
from .formatter import MarkdownFormatter
from .github_client import CommitInfo, FileChange, GitHubClient

logger = logging.getLogger(__name__)


class CommitAnalyzer:
    """Analyzes GitHub commits using Claude AI."""

    def __init__(
        self,
        github_client: Optional[GitHubClient] = None,
        claude_client: Optional[ClaudeClient] = None,
    ):
        """Initialize the analyzer.

        Args:
            github_client: GitHub client instance. If not provided, creates a new one.
            claude_client: Claude client instance. If not provided, creates a new one.
        """
        self.github_client = github_client or GitHubClient()
        self.claude_client = claude_client or ClaudeClient()
        self.config = get_config()
        logger.info("CommitAnalyzer initialized")

    def analyze_by_url(
        self, commit_url: str, language: str = "korean"
    ) -> Tuple[CommitInfo, str]:
        """Analyze a commit by its GitHub URL.

        Args:
            commit_url: GitHub commit URL
            language: Language for analysis ('korean' or 'english')

        Returns:
            Tuple of (CommitInfo, analysis_text)
        """
        logger.info(f"Starting analysis for URL: {commit_url}")

        # Fetch commit from GitHub
        commit_info, file_changes = self.github_client.get_commit_by_url(commit_url)

        # Analyze the commit
        analysis = self._analyze_commit(commit_info, file_changes, language)

        return commit_info, analysis

    def analyze_by_sha(
        self, owner: str, repo: str, sha: str, language: str = "korean"
    ) -> Tuple[CommitInfo, str]:
        """Analyze a commit by repository and SHA.

        Args:
            owner: Repository owner
            repo: Repository name
            sha: Commit SHA
            language: Language for analysis ('korean' or 'english')

        Returns:
            Tuple of (CommitInfo, analysis_text)
        """
        logger.info(f"Starting analysis for {owner}/{repo}@{sha}")

        # Fetch commit from GitHub
        commit_info, file_changes = self.github_client.get_commit(owner, repo, sha)

        # Analyze the commit
        analysis = self._analyze_commit(commit_info, file_changes, language)

        return commit_info, analysis

    def _analyze_commit(
        self, commit_info: CommitInfo, file_changes: list[FileChange], language: str
    ) -> str:
        """Perform the actual analysis using Claude.

        Args:
            commit_info: Commit information
            file_changes: List of file changes
            language: Language for analysis

        Returns:
            Analysis text
        """
        # Format the diff
        diff = self.github_client.format_diff(file_changes)

        # Get analysis from Claude
        if language.lower() == "english":
            analysis = self.claude_client.analyze_commit_english(
                commit_message=commit_info.message,
                diff=diff,
                repository=commit_info.repository,
                author=commit_info.author_name,
            )
        else:
            analysis = self.claude_client.analyze_commit(
                commit_message=commit_info.message,
                diff=diff,
                repository=commit_info.repository,
                author=commit_info.author_name,
            )

        return analysis

    def generate_report(
        self,
        commit_info: CommitInfo,
        file_changes: list[FileChange],
        analysis: str,
        output_path: Optional[Path] = None,
    ) -> str:
        """Generate a Markdown report of the analysis.

        Args:
            commit_info: Commit information
            file_changes: List of file changes
            analysis: Analysis text from Claude
            output_path: Path to save the report. If None, returns the report without saving.

        Returns:
            The generated report content
        """
        analysis_time = datetime.now()
        model = self.claude_client.model

        report = MarkdownFormatter.format_report(
            commit_info=commit_info,
            file_changes=file_changes,
            analysis=analysis,
            analysis_time=analysis_time,
            model=model,
        )

        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(report, encoding="utf-8")
            logger.info(f"Report saved to: {output_path}")

        return report

    def analyze_and_report(
        self,
        commit_url: str,
        output_path: Optional[Path] = None,
        language: str = "korean",
    ) -> str:
        """Analyze a commit and generate a report in one step.

        Args:
            commit_url: GitHub commit URL
            output_path: Path to save the report. If None, returns without saving.
            language: Language for analysis ('korean' or 'english')

        Returns:
            The generated report content
        """
        # Fetch commit information
        commit_info, file_changes = self.github_client.get_commit_by_url(commit_url)

        # Analyze the commit
        analysis = self._analyze_commit(commit_info, file_changes, language)

        # Generate and optionally save the report
        report = self.generate_report(commit_info, file_changes, analysis, output_path)

        return report
