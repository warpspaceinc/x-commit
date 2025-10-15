"""Claude API client for analyzing commit changes."""

import logging
from typing import Optional

from anthropic import Anthropic

from .config import get_config

logger = logging.getLogger(__name__)


class ClaudeClient:
    """Client for interacting with Claude API."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """Initialize Claude client.

        Args:
            api_key: Anthropic API key. If not provided, uses config.
            model: Claude model to use. If not provided, uses config.
        """
        config = get_config()
        self.api_key = api_key or config.anthropic_api_key
        self.model = model or config.claude_model
        self.client = Anthropic(api_key=self.api_key)
        logger.info(f"Claude client initialized with model: {self.model}")

    def analyze_commit(
        self,
        commit_message: str,
        diff: str,
        repository: str,
        author: str,
        max_tokens: int = 4000,
    ) -> str:
        """Analyze a commit using Claude.

        Args:
            commit_message: The commit message
            diff: The diff content
            repository: Repository name
            author: Commit author
            max_tokens: Maximum tokens in response

        Returns:
            Analysis result as markdown text
        """
        logger.info(f"Analyzing commit for {repository}")

        prompt = self._build_analysis_prompt(
            commit_message, diff, repository, author
        )

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            )

            # Extract text from response
            analysis = response.content[0].text

            # Log token usage
            logger.info(
                f"Claude API call completed. "
                f"Input tokens: {response.usage.input_tokens}, "
                f"Output tokens: {response.usage.output_tokens}"
            )

            return analysis

        except Exception as e:
            logger.error(f"Failed to analyze commit with Claude: {e}")
            raise

    def _build_analysis_prompt(
        self, commit_message: str, diff: str, repository: str, author: str
    ) -> str:
        """Build the analysis prompt for Claude."""
        prompt = f"""당신은 숙련된 코드 리뷰어입니다. 다음 GitHub 커밋을 분석하여 팀원들이 이해하기 쉽게 한국어로 요약해주세요.

## 커밋 정보
- **Repository**: {repository}
- **Author**: {author}
- **Commit Message**: {commit_message}

## 변경사항 (Diff)
```diff
{diff}
```

## 분석 가이드라인

**먼저 변경사항의 규모와 성격을 평가하세요:**

1. **간단한 변경 (주석 추가, 포맷팅, 파일 삭제, 오타 수정, 로그 추가 등)**
   - 1-2문장으로 간결하게 요약만 제공
   - 예: "로그 메시지 추가 및 주석 개선"
   - 섹션 구분 없이 핵심만 전달

2. **중간 규모 변경 (작은 기능 추가, 버그 수정, 간단한 리팩토링)**
   - 요약 (2-3문장)
   - 주요 변경사항 (간단하게)
   - 필요시 주의사항만 추가

3. **중요한 변경 (새로운 기능, 아키텍처 변경, 중요한 버그 수정)**
   - 요약 (3-4문장)
   - 주요 변경사항 (상세)
   - 기술적 세부사항
   - 주의사항 및 Breaking changes
   - 필요시 후속 작업 제안

## 작성 원칙
- **간단한 변경은 과도하게 분석하지 마세요** - 1-2문장이면 충분합니다
- 코드의 의도를 파악하여 "무엇을" 했는지보다 "왜" 했는지를 설명하세요
- 명확하고 간결하게 핵심만 전달하세요
- 변경의 중요도에 비례하여 분석 분량을 조절하세요
- 긍정적이고 건설적인 톤을 유지하세요
"""
        return prompt

    def analyze_commit_english(
        self,
        commit_message: str,
        diff: str,
        repository: str,
        author: str,
        max_tokens: int = 4000,
    ) -> str:
        """Analyze a commit using Claude (English version).

        Args:
            commit_message: The commit message
            diff: The diff content
            repository: Repository name
            author: Commit author
            max_tokens: Maximum tokens in response

        Returns:
            Analysis result as markdown text
        """
        logger.info(f"Analyzing commit for {repository} (English)")

        prompt = f"""You are an experienced code reviewer. Analyze the following GitHub commit and provide a clear summary.

## Commit Information
- **Repository**: {repository}
- **Author**: {author}
- **Commit Message**: {commit_message}

## Changes (Diff)
```diff
{diff}
```

## Analysis Guidelines

**First, evaluate the scope and nature of the changes:**

1. **Simple changes (comments, formatting, file deletion, typo fixes, logging, etc.)**
   - Provide only a brief 1-2 sentence summary
   - Example: "Added logging messages and improved comments"
   - No section breakdown needed, just the essence

2. **Medium changes (small feature additions, bug fixes, simple refactoring)**
   - Summary (2-3 sentences)
   - Key changes (brief)
   - Cautions if necessary

3. **Significant changes (new features, architecture changes, critical bug fixes)**
   - Summary (3-4 sentences)
   - Key changes (detailed)
   - Technical details
   - Cautions and breaking changes
   - Follow-up suggestions if needed

## Writing Principles
- **Don't over-analyze simple changes** - 1-2 sentences is enough
- Explain "why" rather than just "what"
- Be clear and concise, focus on essentials
- Scale analysis length proportionally to change importance
- Maintain a positive and constructive tone
"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            )

            analysis = response.content[0].text
            logger.info(
                f"Claude API call completed. "
                f"Input tokens: {response.usage.input_tokens}, "
                f"Output tokens: {response.usage.output_tokens}"
            )

            return analysis

        except Exception as e:
            logger.error(f"Failed to analyze commit with Claude: {e}")
            raise
