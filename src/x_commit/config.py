"""Configuration management for x-commit."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class Config:
    """Application configuration."""

    # Required settings
    github_token: str
    anthropic_api_key: str

    # Optional settings
    github_default_repo: Optional[str] = None
    claude_model: str = "claude-sonnet-4-5-20250929"

    # Slack settings (Phase 2)
    slack_bot_token: Optional[str] = None
    slack_signing_secret: Optional[str] = None
    slack_app_token: Optional[str] = None
    slack_channel: Optional[str] = None
    slack_auto_analyze: bool = False  # If True, auto-analyze all commits; If False, only respond to @mentions
    slack_target_branches: Optional[list[str]] = None  # If set, only analyze commits from these branches

    # Application settings
    log_level: str = "INFO"
    output_dir: Path = Path("./reports")
    max_diff_lines: int = 1000

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        github_token = os.getenv("GITHUB_TOKEN")
        if not github_token:
            raise ValueError(
                "GITHUB_TOKEN environment variable is required. "
                "Please set it in your .env file or environment."
            )

        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        if not anthropic_api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable is required. "
                "Please set it in your .env file or environment."
            )

        output_dir = Path(os.getenv("OUTPUT_DIR", "./reports"))
        output_dir.mkdir(parents=True, exist_ok=True)

        # Parse target branches (comma-separated list)
        target_branches = None
        branches_env = os.getenv("SLACK_TARGET_BRANCHES")
        if branches_env:
            target_branches = [b.strip() for b in branches_env.split(",") if b.strip()]

        return cls(
            github_token=github_token,
            anthropic_api_key=anthropic_api_key,
            github_default_repo=os.getenv("GITHUB_DEFAULT_REPO"),
            claude_model=os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5-20250929"),
            slack_bot_token=os.getenv("SLACK_BOT_TOKEN"),
            slack_signing_secret=os.getenv("SLACK_SIGNING_SECRET"),
            slack_app_token=os.getenv("SLACK_APP_TOKEN"),
            slack_channel=os.getenv("SLACK_CHANNEL"),
            slack_auto_analyze=os.getenv("SLACK_AUTO_ANALYZE", "false").lower() in ("true", "1", "yes"),
            slack_target_branches=target_branches,
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            output_dir=output_dir,
            max_diff_lines=int(os.getenv("MAX_DIFF_LINES", "1000")),
        )


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config
