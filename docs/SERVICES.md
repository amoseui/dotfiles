# Mac mini 서비스·대시보드 인벤토리

확인일: 2026-07-25. 비밀값과 런타임 캐시는 저장소에 포함하지 않는다.

## 1. Hermes Gateway

- 설치: `~/.hermes/hermes-agent`의 git 설치, Hermes Agent `v0.19.0`.
- 실행: launchd label `ai.hermes.gateway`.
- 재생성: `hermes gateway start`가 현재 설치 경로로 plist를 다시 만든다.
- 현재 상태: launchd PID가 실행 중이지만 plist가 현재 설치보다 오래되어 stale 경고가 있었다.
- 복원: 기존 plist를 복사하지 말고 Mac Studio에서 `hermes gateway start`로 생성한다.
- 상태 확인: `hermes gateway status`, `hermes doctor`, Discord 응답.
- 로그: `~/.hermes/logs/gateway.log`, `gateway.error.log` — 백업 제외.

## 2. Hermes WebUI

- 소스: `https://github.com/nesquena/hermes-webui.git`.
- Mac mini checkout: `~/Workspace/github/hermes-webui`, `master`가 2026-07-25 기준 upstream보다 뒤처져 있음.
- Mac mini 현재 실행: `server.py`, direct HTTPS `0.0.0.0:8787`.
- 영속 경로: `~/.hermes/webui/`; 세션, signing key, auth state가 섞여 있어 Git 백업 제외.
- 로컬 설정: checkout의 `.env`; 키 이름은 `HERMES_WEBUI_HOST`, `HERMES_WEBUI_PORT`, `HERMES_WEBUI_TLS_CERT`, `HERMES_WEBUI_TLS_KEY`이며 값은 Git 제외. 복원 wrapper는 direct TLS 키를 비워 Tailscale Serve만 사용한다.
- 복원 실행: `services/run-hermes-webui.sh`가 loopback HTTP로 `bootstrap.py --foreground`를 실행하고 launchd `local.hermes.webui`가 감독한다.
- 로컬 헬스체크: `curl -fsS http://127.0.0.1:8787/health`.
- 주의: 현재 프로세스는 오래된 수동/분리 실행이라 `./ctl.sh status`가 stopped로 오인한다. Mac Studio에서는 추적한 launchd 정의로 통일한다.

## 3. Personal Observatory

- 소스: `git@github.com:amoseui/personal-observatory.git`.
- checkout: `~/Workspace/personal-observatory`, `main` clean.
- Mac mini 현재 실행: `.venv/bin/uvicorn personal_observatory.app:app`, direct HTTPS `0.0.0.0:8788`.
- 설정 스냅샷: `services/personal-observatory/config.local.yaml` (`$HOME` 이식 가능 경로).
- 영속 데이터: `data/feed_state.json`(평가/읽음 상태), `data/feed_items.json`(재생성 가능한 feed cache).
- 복원 실행: `services/run-personal-observatory.sh`가 loopback HTTP로 실행되고 launchd `local.personal.observatory`가 감독한다.
- 로컬 헬스체크: `curl -fsS http://127.0.0.1:8788/api/health`.

## 4. Tailscale Serve

두 앱은 인증이 없는 LAN 공개를 막기 위해 항상 `127.0.0.1`에만 bind한다. 원격 HTTPS는
인증서 파일을 앱에 직접 주입하지 않고 Tailscale Serve가 종료한다. Tailscale ACL/기기 인증이
접근 경계가 되며, Hermes WebUI에는 별도로 로컬 `.env`의 `HERMES_WEBUI_PASSWORD`도 설정한다.

```bash
tailscale serve --bg --https=8787 http://127.0.0.1:8787
tailscale serve --bg --https=8788 http://127.0.0.1:8788
tailscale serve status
```

앱 wrapper는 non-loopback host를 거부하고 direct TLS 환경변수를 제거한다. 인증서 로드 실패 시
평문 `0.0.0.0`으로 fallback하는 구성을 만들지 않는다.

## 5. 설치·기동 순서

```bash
# source repositories
git clone https://github.com/nesquena/hermes-webui.git ~/Workspace/github/hermes-webui
git clone git@github.com:amoseui/personal-observatory.git ~/Workspace/personal-observatory

# Personal Observatory dependencies
cd ~/Workspace/personal-observatory
python3.12 -m venv .venv
.venv/bin/pip install -e '.[dev]'

# service files only, then review local config
cd ~/Workspace/github/dotfiles
./scripts/install-services.sh --dry-run
./scripts/install-services.sh
$EDITOR ~/.config/dotfiles/services.env

./scripts/install-services.sh --start
hermes gateway start
tailscale serve --bg --https=8787 http://127.0.0.1:8787
tailscale serve --bg --https=8788 http://127.0.0.1:8788
```

기존 수동 프로세스가 8787/8788을 점유한 상태에서 `--start`하지 않는다.

## 6. 별도 데이터 이전

Git에 넣지 않는 Personal Observatory 로컬 상태는 암호화 디스크/보안 채널용 디렉터리로 별도 복사한다.
스크립트는 `config.local.yaml`의 `feeds.state_path`와 `feeds.items_path`를 해석해 실제 데이터 위치를
백업·복원한다. 설정 파일 자체는 credential 혼입을 막기 위해 데이터 archive에 넣지 않고,
secret이 제거된 `services/personal-observatory/config.local.yaml`을 dotfiles에서 설치한다.

```bash
./scripts/backup-service-data.sh /Volumes/EncryptedBackup
./scripts/restore-service-data.sh /Volumes/EncryptedBackup/service-data-YYYYMMDDHHMMSS-PID
```

Hermes WebUI 세션/auth/signing state와 Hermes `state.db`, sessions, logs는 이전하지 않고 새 머신에서 재생성·재로그인한다.

## 7. 상태 확인

```bash
launchctl print gui/$(id -u)/local.hermes.webui
launchctl print gui/$(id -u)/local.personal.observatory
curl -fsS http://127.0.0.1:8787/health
curl -fsS http://127.0.0.1:8788/api/health
tailscale serve status
hermes gateway status
hermes cron list
```
