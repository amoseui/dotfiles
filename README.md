# dotfiles

Mac 설정과 AI-agent 환경을 재현하기 위한 개인 dotfiles 저장소.

## 구조 (2026-08-23 public/private 분리)

```
dotfiles (public, 이 저장소)      ← 공통 뼈대. 사내 fork의 rebase 베이스
└── private/                      ← submodule: amoseui/dotfiles-private (사외 머신 전용)
```

- **public**: Git, Vim, Tmux, Zsh, Ghostty, Karabiner, Herdr, Brewfile, Claude Code
  범용 설정·스킬(`claude/`), Codex portable 기본값(`codex/`), `link.sh`
- **private** (submodule): Hermes(에이전트·cron·skills·feed-pipeline),
  services·launchd, PKM 계열 Claude 스킬, `shared/note-taking/CORE.md`,
  개인 거버넌스 문서와 머신 운영 스크립트 — `private/README.md` 참고
- **사내 fork**: 이 public repo를 사내 저장소로 fork해 사내 커밋을 rebase로 유지한다.
  `private/` submodule은 초기화하지 않으며, `link.sh`는 private가 없으면 public 링크만 건다.

## 설치

```bash
git clone git@github.com:amoseui/dotfiles.git ~/Workspace/github/dotfiles
cd ~/Workspace/github/dotfiles
git submodule update --init private   # 사외(개인) 머신만
./link.sh
```

`link.sh`는 반복 실행 가능하며, 충돌하는 일반 파일은 timestamp가 붙은 `.old.*` 파일로
백업한다. `private/link.sh`가 있으면 이어서 실행해 개인 링크까지 적용한다.

Mac Studio 등 개인 머신의 전체 백업·복원 절차(Hermes 포함)는
`private/docs/RESTORE.md`를 따른다.

## Git에 넣지 않는 것

- secret 전반: `.env`, OAuth 토큰, API 키, SSH private key, 앱 로그인 세션
- 런타임 상태: state DB, sessions, logs, cron 실행 결과, 대시보드 로컬 데이터
- Obsidian vault와 개인 데이터 원본
- 개인 인프라 상세는 public이 아닌 private submodule에만 둔다

## 관리 규약

- 로컬 설정 변경은 dotfiles-sync 스킬(또는 수동)로 저장소에 반영하고
  scope prefix 커밋 컨벤션(`[claude] ...`)을 따른다.
- 어떤 스크립트도 자동으로 commit/push하지 않는다. push는 항상 사용자 확인 후에만.
- Claude 쪽 백업 파일 중 `claude/hooks/`·`codex/hooks/`의 herdr 스크립트는 herdr가
  live 파일(`~/.claude/hooks/`, `~/.codex/`)을 소유·갱신하므로 symlink하지 않고
  복사 백업으로만 관리한다.
