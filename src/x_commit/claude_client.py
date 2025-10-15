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

## 요청사항
다음 형식으로 분석 결과를 작성해주세요:

### 1. 요약 (3-4문장)
이 커밋의 핵심 목적과 주요 변경사항을 간단히 설명하세요.

### 2. 주요 변경사항
각 파일별로 어떤 변경이 있었는지 구체적으로 설명하세요:
- 파일명: 변경 내용 설명
- 새로운 기능, 버그 수정, 리팩토링 등을 명확히 구분
- 중요한 로직 변경사항 강조

### 3. 기술적 세부사항
- 사용된 기술, 라이브러리, 패턴
- 아키텍처 변경사항
- 성능에 영향을 줄 수 있는 변경사항

### 4. 주의사항 (해당하는 경우)
- 잠재적 버그나 이슈
- 테스트가 필요한 부분
- 다른 팀원이 알아야 할 중요한 정보
- Breaking changes

### 5. 후속 작업 제안 (선택사항)
필요하다면 추가로 해야 할 작업이나 개선점을 제안하세요.

---

**참고사항:**
- 코드의 의도를 파악하여 "무엇을" 했는지보다 "왜" 했는지를 설명하세요
- 기술적이지 않은 팀원도 이해할 수 있도록 명확하게 작성하세요
- 불필요한 세부사항은 생략하고 핵심만 전달하세요
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

## Analysis Format

### 1. Summary (3-4 sentences)
Briefly explain the core purpose and main changes of this commit.

### 2. Key Changes
Describe changes for each file:
- Filename: Description of changes
- Clearly distinguish between new features, bug fixes, refactoring, etc.
- Highlight important logic changes

### 3. Technical Details
- Technologies, libraries, patterns used
- Architecture changes
- Performance impact

### 4. Cautions (if applicable)
- Potential bugs or issues
- Areas requiring testing
- Important information for team members
- Breaking changes

### 5. Follow-up Suggestions (optional)
Suggest additional work or improvements if needed.

---

**Guidelines:**
- Explain "why" rather than just "what"
- Write clearly for non-technical team members
- Focus on essentials, skip unnecessary details
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
