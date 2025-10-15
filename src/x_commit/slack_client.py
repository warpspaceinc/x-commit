"""Slack API client for posting messages and handling events."""

import logging
from typing import Optional

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from .config import get_config
from .formatter import MarkdownFormatter
from .github_client import CommitInfo, FileChange

logger = logging.getLogger(__name__)


class SlackClient:
    """Client for interacting with Slack API."""

    def __init__(self, token: Optional[str] = None):
        """Initialize Slack client.

        Args:
            token: Slack bot token. If not provided, uses config.
        """
        config = get_config()
        self.token = token or config.slack_bot_token

        if not self.token:
            raise ValueError(
                "SLACK_BOT_TOKEN is required. "
                "Please install the app to your workspace and add the token to .env"
            )

        self.client = WebClient(token=self.token)
        logger.info("Slack client initialized")

    def post_message(
        self, channel: str, text: str, thread_ts: Optional[str] = None
    ) -> dict:
        """Post a message to a Slack channel.

        Args:
            channel: Channel ID (e.g., "C1234567890")
            text: Message text (Slack markdown format)
            thread_ts: Optional thread timestamp to reply in a thread

        Returns:
            Response from Slack API

        Raises:
            SlackApiError: If the API call fails
        """
        try:
            response = self.client.chat_postMessage(
                channel=channel, text=text, thread_ts=thread_ts
            )

            logger.info(
                f"Posted message to {channel}"
                + (f" (thread: {thread_ts})" if thread_ts else "")
            )
            return response.data

        except SlackApiError as e:
            logger.error(f"Failed to post message: {e.response['error']}")
            raise

    def update_message(self, channel: str, ts: str, text: str) -> dict:
        """Update an existing message.

        Args:
            channel: Channel ID
            ts: Message timestamp
            text: New message text

        Returns:
            Response from Slack API

        Raises:
            SlackApiError: If the API call fails
        """
        try:
            response = self.client.chat_update(channel=channel, ts=ts, text=text)

            logger.info(f"Updated message {ts} in {channel}")
            return response.data

        except SlackApiError as e:
            logger.error(f"Failed to update message: {e.response['error']}")
            raise

    def post_analysis_result(
        self,
        channel: str,
        thread_ts: str,
        commit_info: CommitInfo,
        analysis: str,
        model: str,
    ) -> dict:
        """Post a commit analysis result to Slack.

        Args:
            channel: Channel ID
            thread_ts: Thread timestamp to reply to
            commit_info: Commit information
            analysis: Analysis text from Claude
            model: Claude model name

        Returns:
            Response from Slack API
        """
        message = MarkdownFormatter.format_slack_message(commit_info, analysis, model)
        return self.post_message(channel, message, thread_ts)

    def post_progress_message(self, channel: str, thread_ts: str) -> dict:
        """Post a progress message while analyzing.

        Args:
            channel: Channel ID
            thread_ts: Thread timestamp to reply to

        Returns:
            Response from Slack API (contains 'ts' for updating later)
        """
        message = ":mag: 커밋을 분석하고 있습니다... (30초 정도 소요됩니다)"
        return self.post_message(channel, message, thread_ts)

    def post_error_message(
        self, channel: str, thread_ts: str, error_message: str
    ) -> dict:
        """Post an error message to Slack.

        Args:
            channel: Channel ID
            thread_ts: Thread timestamp to reply to
            error_message: Error description

        Returns:
            Response from Slack API
        """
        message = f":x: 분석 중 오류가 발생했습니다:\n```{error_message}```"
        return self.post_message(channel, message, thread_ts)

    def get_channel_info(self, channel: str) -> dict:
        """Get information about a channel.

        Args:
            channel: Channel ID

        Returns:
            Channel information

        Raises:
            SlackApiError: If the API call fails
        """
        try:
            response = self.client.conversations_info(channel=channel)
            return response.data["channel"]

        except SlackApiError as e:
            logger.error(f"Failed to get channel info: {e.response['error']}")
            raise

    def get_bot_user_id(self) -> str:
        """Get the bot's user ID.

        Returns:
            Bot user ID (e.g., "U1234567890")

        Raises:
            SlackApiError: If the API call fails
        """
        try:
            response = self.client.auth_test()
            return response.data["user_id"]

        except SlackApiError as e:
            logger.error(f"Failed to get bot user ID: {e.response['error']}")
            raise

    def add_reaction(self, channel: str, timestamp: str, emoji: str) -> dict:
        """Add a reaction emoji to a message.

        Args:
            channel: Channel ID
            timestamp: Message timestamp
            emoji: Emoji name (without colons, e.g., "white_check_mark")

        Returns:
            Response from Slack API

        Raises:
            SlackApiError: If the API call fails
        """
        try:
            response = self.client.reactions_add(
                channel=channel, timestamp=timestamp, name=emoji
            )

            logger.info(f"Added reaction :{emoji}: to message {timestamp}")
            return response.data

        except SlackApiError as e:
            # Don't raise if reaction already exists
            if e.response["error"] == "already_reacted":
                logger.debug(f"Reaction :{emoji}: already exists on {timestamp}")
                return {}
            logger.error(f"Failed to add reaction: {e.response['error']}")
            raise
