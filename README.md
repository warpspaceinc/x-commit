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


### 디버깅

```bash
# 디버그 로그 활성화
uv run x-commit --log-level DEBUG serve
```

## 문의

이슈나 질문이 있으시면 GitHub Issues를 이용해주세요.
