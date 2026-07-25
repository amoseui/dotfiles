# dotfiles

Mac 설정과 AI-agent 환경을 재현하기 위한 개인 dotfiles 저장소.

## 백업 범위

- Git, Vim, Tmux, Zsh
- Claude Code 설정·스킬
- Hermes의 비밀값을 제거한 config, SOUL, custom skills, cron 정의, feed pipeline
- Hermes Gateway, Hermes WebUI, Personal Observatory 서비스 정의와 복원 절차
- Ghostty, cmux, Karabiner
- Homebrew formula/cask/tap, VS Code extensions, global npm packages (`Brewfile`)

Git에 넣지 않는 것:

- `~/.hermes/.env`, `auth.json`, OAuth 토큰, API 키
- SSH private key, `~/.gitcookies`, 앱 로그인 세션
- Hermes state DB, memories, sessions, logs, cron 실행 결과
- Obsidian vault와 개인 데이터 원본
- TLS private key, WebUI auth/signing state, 대시보드 로컬 feed 상태

## Mac mini에서 최신 설정 백업

```bash
cd ~/Workspace/github/dotfiles
./scripts/sync-from-mac.sh
git diff
```

`sync-from-mac.sh`는 Apple Silicon Homebrew(`/opt/homebrew`)에서 `Brewfile`을 다시 만들고,
Karabiner와 Hermes의 재현 가능한 설정을 갱신한다. Todoist 토큰은
`${TODOIST_API_TOKEN}`으로 치환한다. 모든 결과는 권한 `700`의 private staging에서
파싱·secret 검사를 통과한 뒤에만 worktree에 트랜잭션 방식으로 반영된다.

검토 후 직접 commit/push한다. 스크립트는 자동으로 commit하거나 push하지 않는다.

## Mac Studio로 복원

### 1. 저장소와 데이터 준비

```bash
mkdir -p ~/Workspace/github
git clone git@github.com:amoseui/dotfiles.git ~/Workspace/github/dotfiles
cd ~/Workspace/github/dotfiles
```

별도로 다음을 준비한다.

1. Obsidian vault를 iCloud/동기화 도구/암호화 저장장치로 복사
2. SSH key를 암호화 저장장치나 password manager로 이전
3. `hermes/.env.example`을 참고해 Mac Studio의 `~/.hermes/.env` 작성
4. 필요하면 `~/.hermes/google-accounts/` 토큰 디렉터리를 암호화해 이전
5. Personal Observatory 평가/읽음 상태가 필요하면 `backup-service-data.sh`로 암호화 저장장치에 백업

Secret과 OAuth 파일은 Git, 메신저 평문, 일반 압축파일로 전송하지 않는다.

### 2. 사전 점검

```bash
./scripts/bootstrap-mac.sh --dry-run
```

### 3. 패키지와 설정 복원

Apple Silicon Homebrew와 Hermes를 먼저 설치한 뒤 실행한다.

```bash
curl -fsSLo /tmp/hermes-install.sh https://hermes-agent.nousresearch.com/install.sh
less /tmp/hermes-install.sh  # inspect first
bash /tmp/hermes-install.sh
```

```bash
./scripts/bootstrap-mac.sh
```

Hermes WebUI와 Personal Observatory는 소스 저장소를 clone한 후 별도 launchd 정의를 설치한다.

```bash
./scripts/install-services.sh --dry-run
./scripts/install-services.sh
```

Homebrew 패키지가 이미 설치되어 있으면:

```bash
./scripts/bootstrap-mac.sh --skip-brew
```

기존 파일은 덮어쓰기 전에 `.backup.YYYYMMDDHHMMSS`로 보존된다. Git/Vim/Tmux/Zsh,
Claude Code custom assets, Hermes custom skills, Ghostty와 cmux는 symlink된다. Hermes의
`config.yaml`과 `cron/jobs.json`, Karabiner 설정은 앱이 atomic write로 갱신하므로 symlink하지
않고 복사한다. Hermes gateway 종료를 확인한 뒤 mutable 파일을 한 그룹으로 원자 교체하며,
검증 실패 시 전체 그룹을 이전 백업으로 되돌린다.

### 4. 인증과 서비스 검증

```bash
hermes doctor
hermes cron list
hermes gateway start
gh auth status
claude auth status --text
```

수동 확인 항목:

전체 앱·데이터 목록은 `docs/MAC-STUDIO-CHECKLIST.md`를 사용한다.

- Discord, Todoist, Readwise 및 모델 provider secret
- Hermes/OpenAI/Claude OAuth 로그인
- Google Gmail/Calendar 계정 토큰
- GitHub 및 SSH 인증
- Obsidian vault 경로: `~/Obsidian/amoseui/amoseui`
- Tailscale 로그인
- Xcode license와 command-line tools
- Android SDK/Android Studio
- App Store·JetBrains·Google Drive·Slack 등 GUI 앱 로그인

서비스·대시보드의 repo, 포트, TLS, 영속 데이터, launchd와 health check는
`docs/SERVICES.md`에 기록되어 있다.

## 일반 링크만 다시 적용

```bash
./link.sh
```

`link.sh`는 반복 실행 가능하며, 충돌하는 일반 파일은 timestamp가 붙은 `.old.*` 파일로
백업한다. Hermes core config/cron과 Karabiner는 `bootstrap-mac.sh`로 복원한다.