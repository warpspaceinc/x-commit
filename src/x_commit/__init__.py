"""X-Commit: GitHub commit analyzer with Claude AI."""

__version__ = "0.1.0"

from .analyzer import CommitAnalyzer
from .claude_client import ClaudeClient
from .config import Config, get_config
from .github_client import GitHubClient

__all__ = [
    "CommitAnalyzer",
    "ClaudeClient",
    "Config",
    "get_config",
    "GitHubClient",
]
