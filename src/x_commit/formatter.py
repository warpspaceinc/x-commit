"""Formatters for output generation."""

from datetime import datetime
from typing import List, Optional

from .github_client import CommitInfo, FileChange

# 모델별 토큰 단가 (USD per 1M tokens) - input / output
# https://docs.anthropic.com/en/docs/about-claude/models#model-comparison-table
MODEL_PRICING = {
    "claude-opus-4": {"input": 15.0, "output": 75.0},
    "claude-sonnet-4": {"input": 3.0, "output": 15.0},
    "claude-sonnet-4-5": {"input": 3.0, "output": 15.0},
    "claude-haiku-3-5": {"input": 0.80, "output": 4.0},
}


def _get_model_pricing(model_id: str) -> dict:
    """모델 ID에서 가격 정보를 찾는다. 정확한 매칭이 안 되면 prefix 매칭."""
    for key in MODEL_PRICING:
        if key in model_id:
            return MODEL_PRICING[key]
    # 알 수 없는 모델은 Sonnet 단가를 기본값으로
    return MODEL_PRICING["claude-sonnet-4"]


def format_cost_summary(input_tokens: int, output_tokens: int, model_id: str) -> str:
    """토큰 사용량과 비용을 포맷팅한다."""
    pricing = _get_model_pricing(model_id)
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    total_cost = input_cost + output_cost
    return (
        f"📊 `{model_id}` | "
        f"input: `{input_tokens:,}` · output: `{output_tokens:,}` tokens | "
        f"💰 `${total_cost:.4f}`"
    )


class MarkdownFormatter:
    """Formatter for generating Markdown reports."""

    @staticmethod
    def format_report(
        commit_info: CommitInfo,
        file_changes: List[FileChange],
        analysis: str,
        analysis_time: datetime,
        model: str,
    ) -> str:
        """Format a complete analysis report in Markdown.

        Args:
            commit_info: Commit information
            file_changes: List of file changes
            analysis: Claude's analysis text
            analysis_time: Time when analysis was performed
            model: Claude model used

        Returns:
            Formatted Markdown report
        """
        report_parts = [
            "# 커밋 분석 리포트",
            "",
            "## 📋 커밋 정보",
            "",
            f"- **Repository**: [{commit_info.repository}](https://github.com/{commit_info.repository})",
            f"- **Commit**: [`{commit_info.sha[:8]}`]({commit_info.url})",
            f"- **Author**: {commit_info.author_name} <{commit_info.author_email}>",
            f"- **Date**: {commit_info.date.strftime('%Y-%m-%d %H:%M:%S')}",
            f"- **Files Changed**: {commit_info.files_changed} files (+{commit_info.additions} -{commit_info.deletions})",
            "",
            "### 커밋 메시지",
            "```",
            commit_info.message,
            "```",
            "",
            "---",
            "",
            "## 🔍 AI 분석 결과",
            "",
            analysis,
            "",
            "---",
            "",
            "## 📁 변경된 파일 목록",
            "",
        ]

        # Add file changes summary
        for change in file_changes:
            status_emoji = {
                "added": "✨",
                "removed": "🗑️",
                "modified": "✏️",
                "renamed": "📝",
            }.get(change.status, "📄")

            report_parts.append(
                f"- {status_emoji} **{change.filename}** ({change.status}): "
                f"+{change.additions} -{change.deletions}"
            )

        report_parts.extend(
            [
                "",
                "---",
                "",
                f"*분석 일시: {analysis_time.strftime('%Y-%m-%d %H:%M:%S')}*  ",
                f"*분석 모델: {model}*  ",
                f"*생성: [x-commit](https://github.com/caveduck/x-commit)*",
            ]
        )

        return "\n".join(report_parts)

    @staticmethod
    def format_slack_message(
        commit_info: CommitInfo,
        analysis: str,
        model: str,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
    ) -> str:
        """Format analysis for Slack message.

        Args:
            commit_info: Commit information
            analysis: Claude's analysis text
            model: Claude model used
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens used

        Returns:
            Formatted message for Slack
        """
        # Slack has a 40,000 character limit for messages
        max_length = 39000
        truncated = False

        message_parts = [
            f"*🔍 커밋 분석 완료*",
            "",
            f"*Repository:* <https://github.com/{commit_info.repository}|{commit_info.repository}>",
            f"*Commit:* <{commit_info.url}|`{commit_info.sha[:8]}`>",
            f"*Author:* {commit_info.author_name}",
            f"*Changes:* {commit_info.files_changed} files (+{commit_info.additions} -{commit_info.deletions})",
            "",
            "---",
            "",
            analysis,
        ]

        message = "\n".join(message_parts)

        # Truncate if too long
        if len(message) > max_length:
            message = message[:max_length] + "\n\n...(메시지가 너무 길어 생략되었습니다)"
            truncated = True

        # Add footer with cost summary
        footer_parts = []
        if truncated:
            footer_parts.append("_일부 내용이 생략되었습니다_")

        if input_tokens is not None and output_tokens is not None:
            footer_parts.append(format_cost_summary(input_tokens, output_tokens, model))
        else:
            footer_parts.append(f"_분석 모델: {model}_")

        message += "\n\n---\n" + "\n".join(footer_parts)

        return message

    @staticmethod
    def format_short_summary(commit_info: CommitInfo, file_changes: List[FileChange]) -> str:
        """Format a short summary of the commit.

        Args:
            commit_info: Commit information
            file_changes: List of file changes

        Returns:
            Short summary text
        """
        summary_parts = [
            f"Commit: {commit_info.sha[:8]}",
            f"Author: {commit_info.author_name}",
            f"Date: {commit_info.date.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Changes: {commit_info.files_changed} files (+{commit_info.additions} -{commit_info.deletions})",
            "",
            "Message:",
            commit_info.message,
            "",
            "Files:",
        ]

        for change in file_changes[:10]:  # Limit to 10 files
            summary_parts.append(f"  - {change.filename} ({change.status})")

        if len(file_changes) > 10:
            summary_parts.append(f"  ... and {len(file_changes) - 10} more files")

        return "\n".join(summary_parts)


class ConsoleFormatter:
    """Formatter for console output with colors."""

    @staticmethod
    def format_progress(message: str) -> str:
        """Format a progress message for console output.

        Args:
            message: Progress message

        Returns:
            Formatted message
        """
        return f"[*] {message}..."

    @staticmethod
    def format_success(message: str) -> str:
        """Format a success message for console output.

        Args:
            message: Success message

        Returns:
            Formatted message
        """
        return f"[OK] {message}"

    @staticmethod
    def format_error(message: str) -> str:
        """Format an error message for console output.

        Args:
            message: Error message

        Returns:
            Formatted message
        """
        return f"[ERROR] {message}"

    @staticmethod
    def format_warning(message: str) -> str:
        """Format a warning message for console output.

        Args:
            message: Warning message

        Returns:
            Formatted message
        """
        return f"[WARNING] {message}"

    @staticmethod
    def format_info(message: str) -> str:
        """Format an info message for console output.

        Args:
            message: Info message

        Returns:
            Formatted message
        """
        return f"[INFO] {message}"
