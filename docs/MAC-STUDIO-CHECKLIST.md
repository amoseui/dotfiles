# Mac Studio 수동 이전 체크리스트

Mac mini에서 확인한 앱과 데이터. Homebrew Cask가 확인된 앱은 `Brewfile`로 옮겼고,
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
- Ghostty: 현재 앱 설치 snapshot은 없고 설정만 dotfiles에 포함

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
- [ ] `hermes cron list`에서 8개 job 확인
- [ ] `hermes gateway start` 후 Discord 응답 확인
- [ ] `local.hermes.webui` launchd와 loopback HTTP 8787 health 확인
- [ ] `local.personal.observatory` launchd와 loopback HTTP 8788 health 확인
- [ ] Gmail/Calendar/Todoist/Readwise 연동 확인
- [ ] Karabiner right-command → F18 확인
- [ ] Ghostty/cmux/zsh 설정 확인
- [ ] Tailscale 접속 확인
- [ ] `docs/SERVICES.md`의 기동 순서와 별도 데이터 복원 완료
