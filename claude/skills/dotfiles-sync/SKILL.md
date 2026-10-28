---
name: dotfiles-sync
description: |
  로컬 설정 변경을 dotfiles 저장소(예: ~/dotfiles)에 반영하고 commit / push하는 스킬.
  새 config 파일 추가, 기존 설정 편집(zsh / vim / tmux / git / claude 등), AI 에이전트 설정 변경을
  dotfiles repo로 동기화할 때 사용한다.
  "이거 dotfiles에 반영해줘", "dotfiles 업데이트", "dotfiles에 추가/커밋/push", "설정 백업",
  "방금 바꾼 설정 저장소에 넣어줘", "~/.config/ghostty/config를 dotfile로 추가해줘"처럼
  임의 경로를 지정해 추가해달라는 요청을 언급하거나,
  ~/.claude · ~/.zshrc · ~/.vimrc · ~/.tmux.conf · ~/.gitconfig · ~/.config/* 등
  dotfiles가 관리하거나 관리하면 좋을 설정 파일을 수정/추가한 뒤 저장소에 반영하려는 모든 상황에서
  반드시 사용한다.
  특히 statusline, settings.json, agents, commands, skills 같은 Claude Code 설정을 바꾼 직후라면
  사용자가 명시적으로 요청하지 않아도 이 스킬로 동기화를 제안한다.
  사용자가 어느 작업 디렉터리에 있든(저장소 밖이어도) 동작한다.
---

# dotfiles-sync — 로컬 설정 → 저장소 동기화

## Claude / Codex 호환

- Claude는 `~/.claude/skills/dotfiles-sync`, Codex는 `~/.agents/skills/dotfiles-sync`에서 같은 스킬을 읽는다.
- Codex에서는 `$dotfiles-sync`로 호출하거나 이 파일을 직접 읽는다. `Read/Edit/Write/Bash`는 현재 제공된 파일·쉘 도구로 대응한다.
- 현재 요청·환경에서 저장소의 절대 경로가 확인됐으면 그대로 사용한다. `.git`은 디렉터리뿐 아니라 worktree/submodule의 파일일 수도 있다.
- Codex 전역 지침은 `codex/AGENTS.md` → `~/.codex/AGENTS.md`, 공용 스킬은 `claude/skills/` → `~/.agents/skills/`도 점검한다.
- `~/.codex/config.toml`은 앱이 갱신하는 머신 로컬 파일이다. 통째로 복사하거나 symlink하지 않는다. 공통 기본값만 `codex/defaults.toml`에 선별한다. 적용 스크립트 실행은 live 변경 권한이 있을 때만 한다.
- Codex hooks와 Herdr 스크립트는 copy 백업이다. hook trust hash, 프로젝트 신뢰·승인 규칙, 인증·세션·캐시, 앱이 생성한 MCP 경로는 백업하지 않는다.
- `/codex:*` 리뷰는 Claude 플러그인 명령이다. Codex에서는 native review 또는 별도 컨텍스트의 검토자를 쓰고 실제 검토 범위를 보고한다.

승인된 설정 변경을 repo에 반영하고 배치·관리 방식·검증 결과를 보고한다.
stage·commit·push와 live restore/link는 현재 요청에 포함된 명시적 권한 안에서만 한다.
"검토만", "no stage/commit", "live 변경 금지" 제한은 모든 후속 단계에 유지한다.
이미 승인된 가역적 작업에 같은 허가를 다시 묻지 않는다.

## 기준점 1: public/private 배치는 AGENTS.md가 진실

작업 전에 `$REPO/AGENTS.md`를 읽고 새 파일마다 순서대로 판정한다.

1. secret·타인 PII·머신 로컬 상태 → git 밖. **private에도 금지**다. credential은 수집하거나 읽지 않고 백업에 `${ENV_VAR}` 같은 placeholder만 남긴다.
2. 개인 머신 전용 도구·개인 인프라·일상 구조 → `private/`.
3. 사내 fork가 rebase 베이스로 필요로 하는 공통 설정 → public.

"노출 무해" 또는 "범용적인 코드"만으로 public을 선택하지 않는다. 개인 도구의 백업·복구·E2E와
그 테스트·문서는 stdlib만 써도 Q2다. 공용 sync·보안 검수 primitive는 사내 fork의 필요를
확인해 Q3로 둔다. 검토된 sanitized 개인 snapshot/intake inventory manifest는 private에
둘 수 있다. raw credential·타인 PII와 일회성 실행·복구 manifest, recovery journal·
실행 보고서·로그 등 머신 로컬 산출물은 git 밖이다. 배치가 모호하면 해당 결정을 확인한다.

`ghostty/config`의 공통 UI 설정, `codex/plugins.toml`·`claude/skills/make-pr/config.yaml`의
범용 기본값과 공용 Herdr hooks는 public이다. 앱이 만든 template 주석의 머신 절대경로는
중립적인 설명으로 바꾼다. 그 주석 때문에 도구 전체를 private으로 옮기지 않는다.
기존 미커밋 변경은 같은 도구의 파일이어도 승인 없이 편집하지 않는다.

### 선택적 private 확장

[개인 sync 확장](../../../private/docs/DOTFILES-SYNC.md)은 repo 내 탐색용 링크다.
홈 디렉터리의 skill symlink로 읽으면 Markdown 상대경로가 달라질 수 있으므로,
아래 저장소 경로 찾기로 `REPO`를 먼저 확인한 뒤 `$REPO/private/docs/DOTFILES-SYNC.md`를
조회·읽는다. 제공되는 checkout에서는 개인 자산의 수집·검증 entrypoint와 위험도 기준을 따른다.
없으면 public만 작업하며
private을 생성·초기화하거나 submodule tooling으로 강제로 연결하지 않는다.
public 검증은 이 확장 없이 동작해야 한다. 확장이 있어도 live restore/link 권한은 생기지 않는다.
개인 프로필·일정·인프라 inventory와 구현 상세는 이 공용 스킬에 복제하지 않는다.

## 기준점 2: 배치와 symlink/copy는 독립적인 판단

repo 경로 ↔ 홈 목적지 매핑은 `$REPO/link.sh`에서 읽는다. private 작업이 포함되고 파일이
있으면 `$REPO/private/link.sh`도 읽는다. Python `files = ( ... )` 튜플의 단건 매핑과
디렉터리 자식 링크를 모두 확인한다. 기억에 의존해 매핑이나 목적지를 바꾸지 않는다.

| 관리 방식 | 대상 | repo 반영 후 처리 |
|---|---|---|
| symlink | 사람이 편집하는 정적 파일 | 기존 링크 확인, 새 링크는 live 변경 권한이 있을 때만 적용 |
| copy 백업 | 앱이 atomic write로 갱신하는 설정·hooks | sanitized regular file로 보관, symlink 절차로 넘어가지 않음 |

copy 대상은 `link.sh`에 추가하지 않는다. 개인 도구의 수집·복구 상세는 private 확장에서 다룬다.

## 저장소 경로 찾기

현재 요청·환경에서 확인된 절대 경로를 우선한다. 없으면 다음 머신 로컬 파일을 읽는다.
경로를 추측해서 탐색하지 않는다. `.git` 디렉터리와 파일을 모두 허용한다.

```bash
STATE="${XDG_STATE_HOME:-$HOME/.local/state}/dotfiles-sync/repo-path"
if [ -f "$STATE" ] && [ -e "$(cat "$STATE" 2>/dev/null)/.git" ]; then
  REPO=$(cat "$STATE")
  echo "REPO=$REPO"
else
  echo "NOT_CONFIGURED"
fi
```

`REPO=...`면 다시 묻지 않는다. 확인된 경로도 없고 `NOT_CONFIGURED`면 절대 경로를 한 번 묻고,
실제 Git checkout인지 read-only 명령으로 확인한다. read-only/no-live 요청이면 상태 파일도
쓰지 않는다. 로컬 상태 저장이 허용됐을 때만 다음 예제를 실행한다.

```bash
REPO="<확인된 절대 경로>"
STATE="${XDG_STATE_HOME:-$HOME/.local/state}/dotfiles-sync/repo-path"
if [ -e "$REPO/.git" ]; then
  mkdir -p "$(dirname "$STATE")"
  printf '%s\n' "$REPO" > "$STATE"
fi
```

상태 파일은 git 밖에 둔다. 이후 명령은 cwd와 무관하게 `REPO` 절대 경로를 기준으로 한다.

`REPO`를 확인한 뒤 선택적 확장의 존재만 다음처럼 조회한다. 출력된 경로의 문서를 읽고
작업하며, 출력이 없으면 public-only로 진행한다. 이 예제는 private을 생성·초기화하지 않는다.

```bash
PRIVATE_SYNC="$REPO/private/docs/DOTFILES-SYNC.md"
if [ -f "$PRIVATE_SYNC" ]; then
  printf '%s\n' "$PRIVATE_SYNC"
fi
```

## 작업 순서

### 1. 범위와 source를 확인한다

public 및 작업에 포함된 private 각각의 경로·브랜치·HEAD·dirty 상태와 기존 staged 경로를
기록하고 승인된 파일 목록을 정한다. 기존 미커밋 변경은 보존한다.

```bash
git -C "$REPO" status --short
git -C "$REPO" diff --cached --name-only
```

승인된 경로만 비교한다. untracked 파일을 일괄 읽지 않는다. live auth·`.env`·credential,
제외된 source·세션·캐시를 열지 않는다. API 데이터가 필요하면 해당 환경에서 승인된
수집 도구와 그 출력만 사용한다. 구체적인 개인 수집 명령·경로는 private 확장을 따른다.
승인된 도구나 출력이 없으면 사용자에게 요청한다.

source와 repo destination, 배치, 관리 방식, 적용 방향을 먼저 기록한다. mtime만으로 최신성을
판단하지 않는다. drift는 양쪽 diff를 근거로 처리하고 방향이 모호하면 확인한다.

### 2. 승인된 파일만 repo에 반영한다

- **copy 백업**: 승인된 source 목록을 수집·비교하고 destination에 sanitized regular file을 만든다. raw source 검증과 sanitized destination 검증을 구분한다. 기존 curated text/code를 일괄 덮어쓰지 않는다. symlink 생성과 `link.sh` 기록 단계로 넘어가지 않는다.
- **정상 symlink**: repo diff만 확인한다. 이미 올바른 링크를 다시 만들지 않는다.
- **drift / 신규 정적 파일**: 비교해 정한 방향으로 repo 사본을 갱신하고 fixture에서 검증한다. 실제 홈 링크 적용은 현재 요청이 허용할 때만 한다.

임의 경로도 먼저 Q1/Q2/Q3와 관리 방식을 판정한다. 공통 XDG 설정은 `<tool>/<file>`로 둘 수
있지만 public 여부는 사내 fork의 필요로 판단한다. 신규 정적 링크의 다음 머신용 매핑은
해당 배치의 linker `files` 튜플에 한 줄로 기록한다. 파서가 주석 속 따옴표 쌍을 매핑으로
읽을 수 있으므로 주석에 쌍 예시를 넣지 않는다.

```python
("ghostty/config", ".config/ghostty/config"),
```

live 링크 적용까지 허용된 경우 기존 파일을 충돌 없는 백업 경로에 보존하고 비교·repo 갱신·
단건 링크·readback 순서로 진행한다. symlink 또는 부모 경로 충돌을 우회하지 않는다.
단일 파일을 추가하려고 `link.sh` 전체를 실행하지 않는다. 부트스트랩은 다른 설정과 확장까지
적용할 수 있다. copy 파일은 live 적용 승인이 있어도 symlink로 바꾸지 않는다.
백업과 로컬 산출물은 commit하지 않는다. 외부 산출물을 정리할 때는 삭제보다 이동을 쓴다.

### 3. 위험도에 맞춰 검증·검토한다

| 수준 | 관찰 가능한 조건 | 필수 검증·검토 |
|---|---|---|
| routine | 기존 매핑을 유지하는 작은 공통 설정·문서 변경 | diff와 배치 확인, 영향 있는 fixture 검증, commit 시 결정론 스캔 |
| high-risk | 새 자산 편입, 대량 이동, 구조·linker·복구·sanitization·secret 경계 변경 | 관련 전체 suite와 실제 전달할 checkout의 fixture 검증, 고정된 diff·파일 hash에 대한 독립 검토 |

검증은 임시 fixture와 fake HOME에서만 한다. 실제 사용할 source·전달할 checkout으로 검증하고
축약한 mock 결과를 실제 복구 검증으로 보고하지 않는다. broad sync/restore, live startup,
프로필 script·CLI gateway·cron·network 실행을 검증에 섞지 않는다. fixture는 시스템 임시 경로에
만들고 source dependency로 남기지 않는다. source/destination symlink guard는 유지한다.

공용 계약 회귀 검사는 현재 checkout의 다음 파일로 실행한다.

```bash
python3 -B "$REPO/claude/skills/dotfiles-sync/tests/test_workflow_contract.py" -v
```

이 검사는 실행 예제·portable reference·구체적인 public 배치 위반을 검사한다. agent 행동 검증,
개인 복구 E2E, 독립 검토, secret scan 전체가 통과했다는 뜻은 아니다.
개인 검증 entrypoint는 선택적 확장을 따른다. public-only 작업에는 private suite를 요구하지 않는다.
실제 실행 명령·checkout·exit code·test 수·failure·skip·미검증 범위를 보고한다.
필수 suite가 비었거나 의존성이 없거나 예상하지 않은 skip이면 통과로 처리하지 않는다.

Herdr를 사용하는 작업은 구현 pane과 별도 테스트 pane을 쓴다. 기존 focus를 보존하고 지원되는
`--no-focus` 옵션을 쓴다. 부모가 전용 pane을 관리하면 명령을 전달하고 결과를 기다린다.
작업 중 직접 만든 완료 pane만 닫는다. 기존 pane·process를 정리하지 않는다.

high-risk 검토에는 승인된 경로 목록, 배치 근거, 실제 checkout의 public/private HEAD와 dirty
상태, 검토 대상 파일의 SHA-256, diff, 검증 결과를 제공한다. 보고서는 git 밖에 둔다.
사용자가 지정한 검토자·모델·reasoning을 따른다. 일상 변경에 Opus/max 같은 고비용 모델을
일괄 강제하지 않는다. 접근할 수 없는 검토자를 임의 대체해 통과로 보고하지 않는다.
구체적인 blocker를 수정한 후 영향을 받는 검증과 독립 검토를 다시 수행하고 hash를 갱신한다.
검토 후 변경된 파일은 이전 검토가 보장하지 않는다. 부모가 통합하면 전달 checkout도 다시 확인한다.

### 4. 승인된 경우에만 stage·commit한다

commit을 명시적으로 요청받았을 때만 진행한다. sync·검증 요청만으로 자동 commit하지 않는다.
`no-stage` 제한이 있으면 실제 index를 바꾸지 않는다. 기존 staged 변경도 보존한다.

**결정론 스캔은 매 commit 전 필수**다. 승인된 경로만 stage하고 staged diff가 의도한 범위이며
비어 있지 않은지 확인한 뒤 실행한다. `git add -A` 같은 광범위한 수집은 어떤 index에서도 금지다.
secret·타인 PII·public 배치·linker 계약을 검사한다. scanner를 바꾸면 `--self-test`도 실행한다.

```bash
python3 "$REPO/claude/skills/dotfiles-sync/scripts/precommit_scan.py" "$REPO"
```

이 scanner는 public과 존재하는 private index를 검사한다. 실제 staged 내용을 먼저 확인하고,
선택한 파일만 검사한다고 오해하지 않는다. exit 0만 통과이며 1은 BLOCK, 2는 검사 실패다.
WARN도 결과에 보고한다. 빈 staged diff나 `--tree` 결과를 commit 대상 검증의 대용으로 쓰지 않는다.
`--tree`는 범위 밖 추적 파일도 읽으므로 별도 scope 승인 없이 실행하지 않는다.

no-stage 검증은 승인된 안전한 경로만 임시 index와 필요시 disposable object directory에
선별해 실행하는 검증기를 쓸 수 있다. unsafe `.env`·auth·runtime 후보는 읽기 전에 거부하고,
실제 cached entries가 전후 같음을 확인한다. 그런 검증기가 없으면 scanner 게이트를
**미실행**으로 보고하고 commit 단계에 남긴다. 테스트 통과만으로 secret scan 통과를 주장하지 않는다.

commit 메시지는 영어 `[scope] message` 형식이며 해당 repo 규칙을 따른다.
private 변경은 별도 저장소에서 먼저 commit하고, public gitlink를 그 검증된 SHA로 갱신한 뒤
public commit을 만든다. private 미초기화 public-only 작업은 이 단계 없이 진행한다.

### 5. 승인된 경우에만 push한다

push할 commit과 검증 상태를 요약한다. 현재 요청에서 이미 push를 명시적으로 허용했으면 그
권한을 사용하고, 없으면 확인을 받기 전까지 push하지 않는다. private 변경이 있으면 private을
먼저 push하고 참조할 commit이 원격에 있는지 확인한 뒤 public을 push한다.
공개 gitlink가 원격에서 가져올 수 없는 private SHA를 참조하지 않도록 확인한다.

## 결과 보고

변경 경로·배치 근거·관리 방식, 실제 검증과 미실행/skip, 독립 검토 대상 hash와 결과,
stage·commit·push·live 적용 여부를 구분해 보고한다. fixture 통과와 live 적용을 혼동하지 않는다.
이 스킬은 dotfiles 저장소에 적용하며 다른 저장소 변경으로 범위를 넓히지 않는다.
