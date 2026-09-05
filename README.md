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

## Codex

`link.sh`는 `codex/AGENTS.md`를 `~/.codex/AGENTS.md`에 연결하고 공용 스킬
`dotfiles-sync`, `handoff`, `make-pr`를 `~/.agents/skills/`에도 연결한다.
private가 있으면 개인 PKM 스킬과 공통 참조도 같은 스킬 루트에 연결한다.
Claude의 기존 경로는 유지하며 두 에이전트가 같은 원본을 사용한다.

모델 기본값은 링크 설치와 별도로 명시적으로 적용한다(Python 3.11 이상):

```bash
bash scripts/apply-codex-defaults.sh
python3 scripts/test_codex_defaults.py
```

`codex/defaults.toml`은 현재 선택한 모델·reasoning·service tier와 프로젝트 문서
fallback만 보관한다. 적용 스크립트는 기존 config를 로컬 `config.toml.old.*`로
백업하고 다른 설정을 보존한다. `CLAUDE.md` fallback은 해당 디렉터리에
`AGENTS.md`가 없을 때만 사용하며 두 파일을 합쳐 읽는 설정이 아니다.

`~/.codex/config.toml` 전체는 머신 로컬 파일로 유지한다. 인증, 세션, hook trust,
승인 규칙, 프로젝트 신뢰, 앱이 생성한 MCP·marketplace 경로는 Git에 넣지 않는다.
`CODEX_HOME`을 따로 쓰는 머신에서는 config 적용 스크립트가 그 경로를 따르며,
전역 지침은 해당 디렉터리에 별도로 연결한다(기본 `link.sh` 계약은 `~/.codex`).

CodeGraph를 설치한 머신에서는 다음과 같이 MCP를 등록하고 확인할 수 있다:

```bash
codex mcp add codegraph -- codegraph serve --mcp
codex mcp list
```

플러그인은 Codex 설정에서 설치·활성화한다. Claude의 `enabledPlugins`를 복사해도
Codex에 설치되지 않는다. 공통 워크플로우에 쓰는 `superpowers`, `skill-creator`,
`security-guidance`, `ralph-loop`는 각각 Codex 쪽 설치 상태를 확인한다.
앱의 Browser·문서·Sites 플러그인은 앱이 설치한 경로를 사용한다.

설정·전역 지침 적용 후 새 Codex 세션에서 스킬 목록을 확인한다. CLI에서는
`/skills` 또는 `$dotfiles-sync`·`$handoff`·`$make-pr`로 선택할 수 있다.
herdr hook 복원은 복사 방식으로 하고, 바뀐 hook은 CLI `/hooks`에서 직접 검토·신뢰한다.
기존 trust hash를 다른 머신에 복제하지 않는다.

공식 문서: [전역·프로젝트 지침](https://learn.chatgpt.com/docs/agent-configuration/agents-md),
[스킬 검색 경로](https://learn.chatgpt.com/docs/build-skills),
[훅과 신뢰](https://learn.chatgpt.com/docs/hooks).
