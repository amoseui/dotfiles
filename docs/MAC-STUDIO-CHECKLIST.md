# Mac Studio 수동 이전 체크리스트

이전 Mac 환경에서 확인한 앱과 데이터. Homebrew Cask가 확인된 앱은 `Brewfile`로 옮겼고,
아래에는 App Store·vendor installer·앱 자체 manager가 필요한 항목만 남긴다.

## Brewfile로 자동 복원

- Claude, Clockify Desktop, cmux, Cursor, Discord, Figma, Firefox, Google Chrome
- Google Drive, iTerm2, JetBrains Toolbox, Karabiner-Elements, Notion, Obsidian
- Readwise Reader, Readdle Spark, Rectangle, Slack, Tailscale, Todoist, VS Code, Zoom

## 여전히 수동/App Store 복원

- App Store: Bear, Developer (WWDC), Keynote, UnicornMac, Xcode, KakaoTalk, feedly
- JetBrains Toolbox 관리: Android Studio, CLion, IntelliJ IDEA Community Edition
- vendor/기타: ChatGPT, Claude Code URL Handler, CuaDriver, Orca, Samsung Portable SSD
- Chrome 앱: Google Docs, Google Sheets, Google Slides
- Ghostty: 2026-08-04 brew cask로 설치되어 Brewfile에 등재 (설정·테마는 기존대로 dotfiles symlink)

## 별도 데이터와 인증

- `~/Obsidian/amoseui` vault
- `~/.ssh/` 중 public/private key와 config (암호화 전송)
- `~/.hermes/.env`, `auth.json` (Git 금지, 가능하면 destination에서 재로그인)
- `~/.hermes/google-accounts/`의 Gmail/Calendar OAuth token
- Personal Observatory `data/feed_state.json`과 `data/feed_items.json` (선택, 암호화 전송)
- Tailscale Serve로 loopback 8787/8788을 tailnet HTTPS에 연결; 인증서 private key 복사 금지
- GitHub CLI, Claude Code, Codex/OpenAI, Discord gateway 로그인
- Google Drive 동기화 폴더
- Android SDK와 emulator 이미지
- Xcode derived data는 이전하지 않고 재생성 권장

## 완료 확인

- [ ] Obsidian vault 파일 수와 최근 문서 확인
- [ ] `gh auth status`와 SSH Git clone 확인
- [ ] `claude auth status --text` 확인
- [ ] `hermes doctor` 통과
- [x] `hermes cron list`에서 8개 job 확인 (2026-08-05)
- [ ] `hermes gateway start` 후 Discord 응답 확인
- [x] `local.hermes.webui` launchd와 loopback HTTP 8787 health 확인 (2026-08-05, password 없음)
- [x] `local.personal.observatory` launchd와 loopback HTTP 8788 health 확인 (2026-08-05)
- [ ] Gmail/Calendar/Todoist/Readwise 연동 확인
- [ ] Karabiner right-command → F18 확인
- [ ] Ghostty/cmux/zsh 설정 확인
- [x] Tailscale Serve의 8787/8788 경로 확인 (2026-08-05)
- [ ] `docs/SERVICES.md`의 기동 순서와 별도 데이터 복원 완료

## 2026-08-05 live 확인 메모

- WebUI, Personal Observatory, llama.cpp의 loopback health가 모두 `ok`.
- `local.hermes.webui`, `local.personal.observatory`, `local.llama.server`가 launchd에서 running.
- `hermes doctor`는 core config/cron/gateway는 통과했지만 npm vulnerability와 SSH password-auth 경고가 남아 있어 전체 체크는 미완료로 유지.
