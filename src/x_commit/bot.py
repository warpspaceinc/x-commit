"""Slack bot server for analyzing GitHub commits."""

import logging
import threading
from typing import Optional

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk.errors import SlackApiError

from .analyzer import CommitAnalyzer
from .config import get_config
from .message_parser import MessageParser
from .slack_client import SlackClient

logger = logging.getLogger(__name__)


class CommitAnalyzerBot:
    """Slack bot that analyzes GitHub commits automatically."""

    def __init__(self):
        """Initialize the bot."""
        self.config = get_config()

        if not self.config.slack_bot_token:
            raise ValueError(
                "SLACK_BOT_TOKEN is required. "
                "Please install the app to your workspace."
            )

        if not self.config.slack_signing_secret:
            raise ValueError("SLACK_SIGNING_SECRET is required.")

        # Initialize Slack app
        self.app = App(
            token=self.config.slack_bot_token,
            signing_secret=self.config.slack_signing_secret,
        )

        # Initialize clients
        self.slack_client = SlackClient()
        self.analyzer = CommitAnalyzer()
        self.parser = MessageParser()

        # Resolve channel ID if channel name is provided
        self.target_channel_id = None
        if self.config.slack_channel:
            self.target_channel_id = self._resolve_channel_id(self.config.slack_channel)

        # Register event handlers
        self._register_handlers()

        logger.info("CommitAnalyzerBot initialized")

    def _resolve_channel_id(self, channel: str) -> str:
        """Resolve channel name to channel ID.

        Args:
            channel: Channel name (#commits) or ID (C08GS45FD8W)

        Returns:
            Channel ID or channel name if resolution fails
        """
        # If it already looks like an ID, return as-is
        if channel.startswith('C') or channel.startswith('G'):
            logger.info(f"Channel '{channel}' is already an ID")
            return channel

        # Remove # prefix if present
        channel_name = channel.lstrip('#')

        try:
            # Try to find channel by name
            # Note: This requires 'channels:read' and 'groups:read' scopes
            response = self.slack_client.client.conversations_list(
                types="public_channel,private_channel",
                limit=1000
            )

            for ch in response.get("channels", []):
                if ch.get("name") == channel_name:
                    logger.info(f"Resolved channel '{channel}' to ID: {ch['id']}")
                    return ch["id"]

            # If not found, return channel name (will be used for matching)
            logger.info(f"Could not resolve channel name '{channel}', will use name for matching")
            return channel_name
        except Exception as e:
            # If scope is missing or API call fails, just use the channel name
            logger.info(f"Could not resolve channel '{channel}' (missing scope or API error), will use name for matching")
            return channel_name

    def _register_handlers(self):
        """Register Slack event handlers."""

        # Register message event handler if auto-analyze mode is enabled
        if self.config.slack_auto_analyze:
            @self.app.event("message")
            def handle_message(event, client, logger):
                """Handle GitHub commit messages - auto-analyze mode."""
                # Ignore threaded messages (replies)
                if event.get("thread_ts"):
                    return

                # Only process messages from configured channel if set
                channel = event.get("channel")
                if self.target_channel_id:
                    # Match by channel ID or try to get channel name and match
                    if channel != self.target_channel_id:
                        # If target is not an ID (e.g., "commits"), try to match channel name
                        # This requires fetching channel info, but we can skip for now
                        # and just compare IDs since Slack always sends channel IDs in events
                        logger.debug(f"Skipping message from channel {channel}, not matching target {self.target_channel_id}")
                        return

                # Check if message has GitHub commit URL in attachments
                # GitHub Slack app uses attachments for commit messages
                commit = None

                # First check attachments (GitHub Slack app uses these)
                if "attachments" in event:
                    for attachment in event["attachments"]:
                        # Check various fields in attachment
                        for field in ["text", "fallback", "title", "title_link", "pretext"]:
                            if field in attachment:
                                commit = self.parser.parse_message(str(attachment[field]))
                                if commit:
                                    logger.debug(f"Found commit URL in attachment.{field}")
                                    break
                        if commit:
                            break

                # Also check message text as fallback
                if not commit:
                    message_text = event.get("text", "")
                    commit = self.parser.parse_message(message_text)
                    if commit:
                        logger.debug("Found commit URL in message text")

                if commit:
                    logger.info(
                        f"Auto-analyzing commit {commit.sha[:8]} from channel {channel}"
                    )
                    # Analyze the commit in a thread
                    threading.Thread(
                        target=self._analyze_and_post,
                        args=(commit, channel, event.get("ts")),
                        daemon=True,
                    ).start()

        @self.app.event("app_mention")
        def handle_mention(event, client, logger):
            """Handle app mentions - analyze commit in thread."""
            # Get the message that was mentioned
            channel = event.get("channel")
            thread_ts = event.get("thread_ts") or event.get("ts")

            # Check if this is a thread reply
            if event.get("thread_ts"):
                # Get the parent message (thread starter)
                try:
                    response = client.conversations_replies(
                        channel=channel,
                        ts=thread_ts,
                        limit=1
                    )
                    parent_message = response["messages"][0]

                    # Debug: Log the full parent message structure
                    logger.info(f"Parent message structure: {parent_message}")

                    parent_text = parent_message.get("text", "")
                    logger.info(f"Parent text content: {parent_text}")

                    # Try to parse from text first
                    commit = self.parser.parse_message(parent_text)

                    # If not found in text, check attachments (GitHub Slack app uses these)
                    if not commit and "attachments" in parent_message:
                        logger.info("Checking attachments for GitHub URL...")
                        for attachment in parent_message["attachments"]:
                            logger.info(f"Attachment: {attachment}")
                            # Check various fields in attachment
                            for field in ["text", "fallback", "title", "title_link"]:
                                if field in attachment:
                                    logger.info(f"Checking attachment.{field}: {attachment[field]}")
                                    commit = self.parser.parse_message(str(attachment[field]))
                                    if commit:
                                        logger.info(f"Found commit in attachment.{field}")
                                        break
                            if commit:
                                break

                    # If still not found, check blocks (Block Kit format)
                    if not commit and "blocks" in parent_message:
                        logger.info("Checking blocks for GitHub URL...")
                        for block in parent_message["blocks"]:
                            logger.info(f"Block: {block}")
                            # Extract text from various block elements
                            if "text" in block and isinstance(block["text"], dict):
                                text_content = block["text"].get("text", "")
                                logger.info(f"Checking block text: {text_content}")
                                commit = self.parser.parse_message(text_content)
                                if commit:
                                    logger.info("Found commit in block text")
                                    break
                            # Check elements in block
                            if "elements" in block:
                                for element in block["elements"]:
                                    if "text" in element:
                                        text_content = element.get("text", "")
                                        logger.info(f"Checking element text: {text_content}")
                                        commit = self.parser.parse_message(text_content)
                                        if commit:
                                            logger.info("Found commit in element text")
                                            break
                            if commit:
                                break

                    if commit:
                        logger.info(
                            f"Analyzing commit {commit.sha[:8]} from mention in thread"
                        )
                        # Analyze the commit
                        threading.Thread(
                            target=self._analyze_and_post,
                            args=(commit, channel, thread_ts),
                            daemon=True,
                        ).start()
                    else:
                        # No commit found in parent message
                        client.chat_postMessage(
                            channel=channel,
                            thread_ts=thread_ts,
                            text=":warning: 쓰레드의 원본 메시지에서 GitHub 커밋 URL을 찾을 수 없습니다.\n\n"
                                 "사용법: GitHub 커밋이 포함된 메시지의 쓰레드에서 `@x-commit`을 멘션하세요."
                        )
                except Exception as e:
                    logger.error(f"Failed to get parent message: {e}")
                    client.chat_postMessage(
                        channel=channel,
                        thread_ts=thread_ts,
                        text=f":x: 메시지를 가져오는 중 오류가 발생했습니다: {e}"
                    )
            else:
                # Direct mention (not in thread)
                # Check current message for commit URL
                message_text = event.get("text", "")
                commit = self.parser.parse_message(message_text)

                if commit:
                    logger.info(f"Analyzing commit {commit.sha[:8]} from direct mention")
                    threading.Thread(
                        target=self._analyze_and_post,
                        args=(commit, channel, event.get("ts")),
                        daemon=True,
                    ).start()
                else:
                    client.chat_postMessage(
                        channel=channel,
                        thread_ts=event.get("ts"),
                        text=":wave: 안녕하세요! X-Commit 봇입니다.\n\n"
                             "*사용법:*\n"
                             "1. GitHub 커밋 메시지의 쓰레드에서 `@x-commit`을 멘션\n"
                             "2. 또는 커밋 URL과 함께 `@x-commit` 멘션\n\n"
                             "*지원하는 URL 형식:*\n"
                             "• `https://github.com/owner/repo/commit/sha`\n"
                             "• Slack 링크: `<https://github.com/...>`\n"
                             "• Markdown: `[text](https://github.com/...)`\n\n"
                             "*예시:*\n"
                             "```\n"
                             "@x-commit https://github.com/owner/repo/commit/abc123\n"
                             "```"
                    )

    def _analyze_and_post(self, commit, channel: str, thread_ts: str):
        """Analyze commit and post result to Slack.

        Args:
            commit: ParsedCommit object
            channel: Slack channel ID
            thread_ts: Thread timestamp to reply to
        """
        try:
            # Post progress message
            progress_response = self.slack_client.post_progress_message(
                channel, thread_ts
            )
            progress_ts = progress_response.get("ts")

            # Add reaction to original message
            try:
                self.slack_client.add_reaction(channel, thread_ts, "mag")
            except Exception as e:
                logger.warning(f"Failed to add reaction: {e}")

            # Analyze the commit
            logger.info(f"Analyzing commit {commit.sha[:8]}...")
            commit_info, file_changes = self.analyzer.github_client.get_commit(
                commit.owner, commit.repo, commit.sha
            )

            analysis = self.analyzer._analyze_commit(
                commit_info, file_changes, "korean"
            )

            logger.info(f"Analysis completed for {commit.sha[:8]}")

            # Update progress message with result
            self.slack_client.post_analysis_result(
                channel, thread_ts, commit_info, analysis, self.config.claude_model
            )

            # Remove progress message if it exists
            if progress_ts:
                try:
                    self.slack_client.client.chat_delete(
                        channel=channel, ts=progress_ts
                    )
                except Exception as e:
                    logger.warning(f"Failed to delete progress message: {e}")

            # Change reaction to check mark
            try:
                self.slack_client.client.reactions_remove(
                    channel=channel, timestamp=thread_ts, name="mag"
                )
                self.slack_client.add_reaction(
                    channel, thread_ts, "white_check_mark"
                )
            except Exception as e:
                logger.warning(f"Failed to update reaction: {e}")

        except Exception as e:
            logger.error(f"Failed to analyze commit: {e}", exc_info=True)

            # Post error message
            try:
                error_msg = str(e)
                if len(error_msg) > 200:
                    error_msg = error_msg[:200] + "..."

                self.slack_client.post_error_message(channel, thread_ts, error_msg)

                # Update reaction to X
                try:
                    self.slack_client.client.reactions_remove(
                        channel=channel, timestamp=thread_ts, name="mag"
                    )
                    self.slack_client.add_reaction(channel, thread_ts, "x")
                except:
                    pass

            except Exception as post_error:
                logger.error(f"Failed to post error message: {post_error}")

    def start_socket_mode(self):
        """Start the bot in Socket Mode (for development/testing)."""
        if not self.config.slack_app_token:
            raise ValueError(
                "SLACK_APP_TOKEN is required for Socket Mode. "
                "Please add it to your .env file."
            )

        logger.info("Starting bot in Socket Mode...")
        handler = SocketModeHandler(self.app, self.config.slack_app_token)
        handler.start()

    def get_app(self):
        """Get the Slack Bolt app instance for HTTP mode.

        Returns:
            Slack Bolt App instance
        """
        return self.app


def create_bot() -> CommitAnalyzerBot:
    """Create and return a CommitAnalyzerBot instance.

    Returns:
        CommitAnalyzerBot instance
    """
    return CommitAnalyzerBot()
