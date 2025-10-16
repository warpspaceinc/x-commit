# X-Commit

GitHub 커밋을 Claude AI로 자동 분석하고 Slack에 결과를 공유하는 도구

## 특징

- 🤖 **AI 기반 코드 분석**: Claude AI가 커밋의 변경사항을 이해하고 상세히 설명
- 💬 **Slack 통합**: 슬랙에서 `@x-commit` 멘션만으로 간편하게 분석
- 🔍 **스마트 파싱**: 다양한 GitHub URL 형식 자동 인식
- 🌏 **다국어 지원**: 한국어/영어 분석 결과 생성
- ⚡ **CLI 도구**: 터미널에서도 바로 사용 가능

## 설치

### 사전 요구사항

- Python 3.11 이상
- [UV 패키지 매니저](https://github.com/astral-sh/uv)
- GitHub Personal Access Token
- Anthropic API Key (Claude)
- Slack Workspace (Slack Bot 사용 시)

### 설치 방법

1. **저장소 클론**
```bash
git clone https://github.com/your-username/x-commit.git
cd x-commit
```

2. **의존성 설치**
```bash
uv sync
```

3. **환경 변수 설정**
```bash
cp .env.example .env
# .env 파일을 열어 API 키 입력
```

필수 환경 변수:
- `GITHUB_TOKEN`: GitHub Personal Access Token
- `ANTHROPIC_API_KEY`: Claude API Key
- `SLACK_BOT_TOKEN`: Slack Bot Token (Slack 사용 시)
- `SLACK_SIGNING_SECRET`: Slack Signing Secret (Slack 사용 시)
- `SLACK_APP_TOKEN`: Slack App Token (Socket Mode 사용 시)

## 사용 방법

### 1. CLI 도구

#### 커밋 분석

GitHub 커밋 URL을 입력하면 상세한 분석 리포트를 생성합니다.

```bash
# 커밋 URL로 분석
uv run x-commit analyze https://github.com/owner/repo/commit/abc123

# 분석 결과를 파일로 저장
uv run x-commit analyze https://github.com/owner/repo/commit/abc123 -o report.md

# 표준 출력으로 결과 보기
uv run x-commit analyze https://github.com/owner/repo/commit/abc123 --stdout

# 영어로 분석
uv run x-commit analyze https://github.com/owner/repo/commit/abc123 --language english
```

#### 메시지 파싱 테스트

Slack 메시지에서 GitHub 커밋 URL을 추출하는 기능을 테스트합니다.

```bash
# GitHub Slack App 형식 파싱
uv run x-commit parse-message "rick pushed to main: https://github.com/owner/repo/commit/abc123 - Fix bug"

# 직접 URL 파싱
uv run x-commit parse-message "https://github.com/owner/repo/commit/abc123"

# 여러 커밋 추출
uv run x-commit parse-message "commits: url1 and url2" --all
```

#### 설정 확인

```bash
# 환경 변수 및 API 연결 확인
uv run x-commit config-check
```

### 2. Slack Bot

Slack에서 `@x-commit`을 멘션하면 자동으로 커밋을 분석합니다.

#### Slack 앱 설정

1. **Slack 앱 생성** (https://api.slack.com/apps)
   - "Create New App" → "From scratch"
   - 앱 이름: `x-commit`
   - 워크스페이스 선택

2. **Bot Token Scopes 추가** (OAuth & Permissions)
   - `app_mentions:read` - 앱 멘션 읽기
   - `channels:history` - 채널 메시지 읽기
   - `chat:write` - 메시지 작성
   - `reactions:write` - 리액션 추가

3. **Event Subscriptions 활성화**
   - Subscribe to bot events:
     - `app_mention` - 앱 멘션 이벤트

4. **Socket Mode 활성화** (개발용)
   - "Socket Mode" → Enable
   - App-level token 생성 (scopes: `connections:write`)

5. **워크스페이스에 설치**
   - "Install to Workspace" 클릭
   - Bot User OAuth Token 복사 → `.env`의 `SLACK_BOT_TOKEN`에 추가
   - App-level token 복사 → `.env`의 `SLACK_APP_TOKEN`에 추가

6. **채널에 봇 추가**
```
/add @x-commit
```

#### 봇 실행

```bash
# Socket Mode로 실행 (개발/테스트용)
uv run x-commit serve

# HTTP Mode로 실행 (프로덕션용)
uv run x-commit serve --mode http --port 3000
```

#### 봇 동작 모드 설정

`.env` 파일에서 `SLACK_AUTO_ANALYZE` 환경변수로 봇의 동작 모드를 선택할 수 있습니다:

**멘션 모드 (기본값)**
```bash
# .env
SLACK_AUTO_ANALYZE=false
```
- `@x-commit`을 멘션했을 때만 분석합니다
- 분석이 필요한 커밋만 선택적으로 분석 가능
- 비용 절감에 유리

**자동 분석 모드**
```bash
# .env
SLACK_AUTO_ANALYZE=true
SLACK_CHANNEL=#commits  # 또는 채널 ID (예: C08GS45FD8W)
```
- 지정된 채널의 모든 GitHub 커밋 메시지를 자동으로 분석합니다
- GitHub Slack App이 포스팅한 커밋 메시지를 자동 감지
- `SLACK_CHANNEL`이 설정되지 않으면 모든 채널을 모니터링합니다

> **참고**: 자동 분석 모드에서는 `message` 이벤트 구독이 필요합니다. Slack 앱 설정에서 "Event Subscriptions" → "Subscribe to bot events"에 `message.channels` 이벤트를 추가하세요.

#### 커밋 메시지 필터링 (.xcommitignore)

특정 패턴의 커밋 메시지를 자동으로 무시하도록 설정할 수 있습니다. 프로젝트 루트에 `.xcommitignore` 파일을 생성하여 제외할 패턴을 정의하세요.

**파일 형식:**
```
# 주석은 # 으로 시작
# 빈 줄은 무시됨

# 문자열 패턴 (대소문자 무시, 부분 일치)
Merge branch
Merge pull request
WIP:
[skip ci]

# 정규표현식 패턴 (regex: 접두사 사용)
regex:^Merge\s+(branch|pull request)
regex:\[skip\s*analyze\]
```

**기본 제공 패턴:**
- `Merge branch` - 머지 커밋 제외
- `Merge pull request` - PR 머지 커밋 제외
- `WIP:`, `[WIP]` - 작업 중인 커밋 제외
- `[skip ci]`, `[ci skip]` - CI 스킵 커밋 제외
- `Bumped version`, `Updated dependencies` - 자동 생성 커밋 제외

**환경변수 설정:**
```bash
# .env
XCOMMIT_IGNORE_FILE=.xcommitignore  # 기본값, 다른 경로 지정 가능
```

#### Slack에서 사용하기

**멘션 모드 사용법**

**방법 1: 쓰레드에서 멘션 (추천)**

1. GitHub 커밋 메시지가 Slack에 포스팅됨
2. 해당 메시지의 쓰레드에 답글 작성
3. `@x-commit` 멘션
4. 봇이 자동으로 원본 메시지의 커밋을 분석!

```
[GitHub 커밋 메시지]
  └─ @x-commit  ← 여기에 멘션!
     └─ [봇의 분석 결과]
```

**방법 2: 커밋 URL과 함께 멘션**

```
@x-commit https://github.com/owner/repo/commit/abc123
```

## 분석 리포트 예시

### CLI 출력

```markdown
# 커밋 분석 리포트

## 📋 커밋 정보

- **Repository**: owner/repo
- **Commit**: `abc123de`
- **Author**: John Doe <john@example.com>
- **Date**: 2025-01-15 14:30:00
- **Files Changed**: 8 files (+990 -42)

### Slack 출력

봇이 쓰레드에 다음과 같이 분석 결과를 포스팅합니다:

```
🔍 커밋 분석 완료

Repository: owner/repo
Commit: abc123de
Author: John Doe
Changes: 8 files (+990 -42)

---

[AI 분석 결과]

분석 모델: claude-sonnet-4-5-20250929
```

## 지원하는 GitHub URL 형식

- **Direct URL**: `https://github.com/owner/repo/commit/sha`
- **Slack Link**: `<https://github.com/owner/repo/commit/sha|View>`
- **Markdown**: `[Commit](https://github.com/owner/repo/commit/sha)`
- **GitHub Slack App**: `user pushed to main: https://... - message`

## 프로젝트 구조

```
x-commit/
├── src/
│   └── x_commit/
│       ├── __init__.py
│       ├── cli.py              # CLI 진입점
│       ├── bot.py              # Slack Bot 서버
│       ├── analyzer.py         # 분석 엔진
│       ├── github_client.py    # GitHub API 클라이언트
│       ├── claude_client.py    # Claude API 클라이언트
│       ├── slack_client.py     # Slack API 클라이언트
│       ├── message_parser.py   # 메시지 파싱
│       ├── ignore_patterns.py  # 패턴 기반 필터링
│       ├── formatter.py        # 출력 포맷터
│       └── config.py           # 설정 관리
├── reports/                    # 생성된 리포트 (기본값)
├── .env                        # 환경 변수 (git ignore)
├── .env.example               # 환경 변수 템플릿
├── .xcommitignore             # 무시할 커밋 패턴
├── pyproject.toml             # 프로젝트 설정
├── PLAN.md                    # 개발 계획
├── SLACK_BOT.md              # Slack Bot 상세 가이드
├── TESTING.md                # 테스트 가이드
└── README.md                 # 이 문서
```

## API 키 발급 방법

### GitHub Token

1. https://github.com/settings/tokens 접속
2. "Generate new token (classic)" 클릭
3. Scopes 선택:
   - `repo` (비공개 저장소 분석 시)
   - `public_repo` (공개 저장소만 분석 시)
4. 생성된 토큰을 `.env`에 저장

### Anthropic API Key

1. https://console.anthropic.com/ 접속
2. Workspace를 "Claude Code"로 선택
3. "API Keys" 메뉴에서 새 키 생성
4. 생성된 키를 `.env`에 저장

## 비용

### Claude API

- **모델**: claude-sonnet-4-5-20250929
- **입력**: $3 / MTok (백만 토큰당)
- **출력**: $15 / MTok

**예상 비용 (커밋당)**:
- 작은 커밋 (1-2 파일): ~$0.01
- 중간 커밋 (5-10 파일): ~$0.05
- 큰 커밋 (20+ 파일): ~$0.10

**월 예상 비용**:
- 하루 10 커밋 × 30일 = ~$9/월
- 하루 50 커밋 × 30일 = ~$45/월

### GitHub API

- **무료**: 시간당 5,000 요청 (인증된 요청)

## 문제 해결

### "GITHUB_TOKEN is required"

`.env` 파일에 GitHub 토큰이 설정되지 않았습니다.

```bash
cp .env.example .env
# .env 파일 편집하여 GITHUB_TOKEN 추가
```

### "invalid x-api-key" (Claude)

Anthropic API 키가 유효하지 않거나 크레딧이 부족합니다.

- Workspace를 "Claude Code"로 변경하여 새 키 생성
- https://console.anthropic.com/settings/plans 에서 크레딧 확인

### Slack Bot이 응답하지 않음

1. **봇이 실행 중인지 확인**
   ```bash
   uv run x-commit serve
   ```

2. **봇이 채널에 추가되었는지 확인**
   ```
   /add @x-commit
   ```

3. **Event Subscriptions 확인**
   - `app_mention` 이벤트가 구독되어 있는지 확인

4. **Socket Mode 활성화 확인**
   - `.env`에 `SLACK_APP_TOKEN`이 설정되어 있는지 확인

### "No commit URL found"

메시지에 유효한 GitHub 커밋 URL이 없습니다.

- URL이 `https://github.com/owner/repo/commit/sha` 형식인지 확인
- SHA는 최소 7자 이상이어야 합니다

## 개발

### 테스트

```bash
# 메시지 파싱 테스트
uv run x-commit parse-message "test message"

# 설정 확인
uv run x-commit config-check

# 커밋 분석 테스트
uv run x-commit analyze https://github.com/torvalds/linux/commit/abc123def
```

### 디버깅

```bash
# 디버그 로그 활성화
uv run x-commit --log-level DEBUG serve
```

## 문의

이슈나 질문이 있으시면 GitHub Issues를 이용해주세요.
