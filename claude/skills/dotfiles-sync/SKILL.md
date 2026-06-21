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

# Dotfiles Sync

로컬에서 바뀐 설정을 dotfiles 저장소에 정확히 반영하고, 일관된 컨벤션으로 commit한 뒤
사용자 확인을 거쳐 push한다.

## 왜 필요한가

이 저장소는 **symlink 방식**으로 동작한다. `link.sh`가 repo 안의 파일을 홈 디렉터리의 실제 위치로
심볼릭 링크해 둔다. 링크가 살아 있는 파일은 편집하면 repo에 자동 반영되지만, 현실에서는 세 가지
상태가 섞인다:

1. **링크 정상** — 편집이 곧 repo 변경 (예: `~/.claude/CLAUDE.md`)
2. **drift** — 링크가 끊겨 홈에 실제 파일이 따로 존재하고 repo 사본과 내용이 어긋남 (예: `settings.json`)
3. **미추적 신규 파일** — 홈에는 있지만 repo에도 없고 `link.sh`에도 없음 (예: `statusline-command.sh`)

사용자가 "dotfiles에 반영해줘"라고 할 때 실제로 원하는 것은 이 세 경우를 모두 올바르게 정리해서
저장소가 홈의 최신 상태와 일치하게 만드는 것이다. 단순히 `git add` 하나로 끝나지 않기 때문에 이
스킬이 존재한다.

## 기준점: link.sh가 매핑의 진실

repo 경로 ↔ 홈 경로 매핑은 **항상 `link.sh`를 읽어서** 파악한다. 추측하지 않는다. 현재 매핑은
대략 다음과 같지만, 작업 전 반드시 `link.sh`를 다시 읽어 최신 상태를 확인한다:

| 홈 경로 | repo 경로 | scope |
|---|---|---|
| `~/.gitconfig`, `~/.gitignore` | `git/` | `git` |
| `~/.tmux.conf` | `tmux/tmux.conf` | `tmux` |
| `~/.zshrc` | `zsh/zshrc` | `zsh` |
| `~/.vimrc` | `vim/vimrc` | `vim` |
| `~/.claude/settings.json`, `CLAUDE.md` | `claude/` | `claude` |
| `~/.claude/{agents,commands,skills}/*` | `claude/{agents,commands,skills}/*` | `claude` |

### 저장소 경로 찾기 (처음 한 번만 입력받아 로컬 파일에 저장)

저장소 경로는 머신마다 다르므로 하드코딩하지 않는다. 또한 **직접 추측해서 찾지 않는다.**
대신 처음 한 번만 사용자에게 경로를 물어 **머신-로컬 파일**에 저장하고, 이후 실행에서는 그 파일에서
읽어 온다. 이렇게 하면 자동 탐색의 오탐 없이, 머신마다 한 번의 입력으로 안정적으로 동작한다.

로컬 저장 위치 (저장소 바깥이라 절대 commit·symlink되지 않음):

```
${XDG_STATE_HOME:-$HOME/.local/state}/dotfiles-sync/repo-path
```

작업을 시작할 때 먼저 이 파일을 읽어 `REPO`를 정한다:

```bash
STATE="${XDG_STATE_HOME:-$HOME/.local/state}/dotfiles-sync/repo-path"
if [ -f "$STATE" ] && [ -d "$(cat "$STATE" 2>/dev/null)/.git" ]; then
  REPO=$(cat "$STATE"); echo "REPO=$REPO"
else
  echo "NOT_CONFIGURED"
fi
```

- `REPO=...`가 나오면 그대로 쓴다. **다시 묻지 않는다.**
- `NOT_CONFIGURED`(처음 쓰는 머신)면 사용자에게 **dotfiles 저장소의 절대 경로**를 한 번 묻는다.
  답을 받으면 `.git`을 가진 디렉터리인지 확인한 뒤 로컬 파일에 저장한다:

  ```bash
  REPO="<사용자가 답한 절대 경로>"        # 예: ~/dotfiles, /Users/you/src/dotfiles
  case "$REPO" in "~"/*) REPO="$HOME/${REPO#~/}";; esac   # ~ 확장
  if [ -d "$REPO/.git" ]; then
    mkdir -p "$(dirname "$STATE")"
    printf '%s\n' "$REPO" > "$STATE"
    echo "saved -> $STATE"
  else
    echo "git 저장소가 아님 — 경로를 다시 확인"
  fi
  ```

  저장 후에는 다음 실행부터 묻지 않는다. 경로가 바뀌면 이 파일을 지우거나 새 경로로 덮어쓴다.
  이 파일은 사용자별·머신별 상태이므로 **절대 repo에 넣지 않는다.**

이 스킬은 **현재 작업 디렉터리에 무관하게** 동작해야 한다. 사용자가 저장소 밖 어디에서 호출하더라도
항상 `REPO` 절대 경로를 기준으로 작업한다. 상대 경로(`cd` 의존)에 기대지 않는다.

## 작업 순서

### 1. 무엇이 바뀌었는지 파악한다

저장소에서 먼저 변경을 확인한다:

```bash
git -C "$REPO" status --short
```

그다음 `link.sh`가 관리하는 각 홈 경로의 **링크 상태**를 점검해 drift와 신규 파일을 찾는다.
파일이 symlink인지(`-L`), 실제 파일인지, repo 사본과 내용이 같은지(`diff`)를 확인한다:

```bash
# 예: 링크 여부 + 내용 차이 확인
ls -la ~/.claude/settings.json
diff ~/.claude/settings.json "$REPO/claude/settings.json"
```

사용자가 방금 특정 파일을 편집했다면(예: 직전 대화에서 statusline을 고쳤다면) 그 파일을 우선
대상으로 삼는다. 범위가 불분명하면 git status에 잡힌 것 + 방금 만진 파일을 기준으로 한다.

### 2. 변경을 repo로 동기화한다

각 파일을 상태에 따라 처리한다:

- **링크 정상** (홈이 이미 repo로 향한 symlink) — 편집이 곧 repo 변경이므로 그대로 둔다.
  (`git status`에 변경으로 잡힘)
- **drift / 미추적 신규 파일** (홈에 실제 파일이 따로 있음) — 아래 **최초 링크 생성 절차**를 따른다.

#### 최초 링크 생성 절차 (백업 → 비교 → 최신화 → 직접 링크)

어떤 파일을 처음 dotfiles 관리 대상으로 삼아 symlink를 걸 때는, 홈 파일을 곧바로 덮어쓰지 않는다.
실수로 더 최신인 홈 내용을 잃을 수 있기 때문이다. 다음 순서를 지킨다:

1. **백업** — 홈의 실제 파일을 `*.old`로 백업해 둔다. 안전망이다.

   ```bash
   SRC=~/.claude/statusline-command.sh        # 홈 경로
   DST="$REPO/claude/statusline-command.sh"   # repo 안 대응 위치
   [ -e "$SRC" ] && [ ! -L "$SRC" ] && cp -p "$SRC" "$SRC.old"
   ```

2. **비교** — repo에 이미 같은 파일이 있으면 홈과 얼마나 일치하는지 본다. 다르면 어느 쪽이 최신인지
   판단한다(보통 방금 편집한 홈 쪽). 모호하면 `diff`를 사용자에게 보여주고 방향을 확인한다.

   ```bash
   [ -e "$DST" ] && diff "$SRC" "$DST"   # 차이가 없으면 출력 없음
   ```

3. **최신화** — 최신 내용을 repo로 반영한다. 홈이 최신이면 홈 → repo로 복사한다. (repo 쪽을 손으로
   고쳐 둔 흔적이 있어 repo가 최신이면 반대 방향일 수도 있으니 비교 결과를 근거로 결정한다.)

   ```bash
   mkdir -p "$(dirname "$DST")"
   cp "$SRC" "$DST"
   ```

4. **직접 심볼릭 링크** — 홈 파일을 repo 사본으로 향하는 symlink로 **직접** 만든다. 이렇게 해야 이후
   편집이 자동으로 repo에 반영된다. (`link.sh`를 실행하지 않는다 — 아래 설명 참고.)

   ```bash
   ln -sfn "$DST" "$SRC"
   ```

5. **link.sh에 기록** — 다음 머신의 최초 설치를 위해 `link.sh`의 해당 섹션에 매핑 한 줄을 추가한다.
   이건 어디까지나 **기록**이며, 지금 링크를 거는 수단이 아니다(링크는 4번에서 이미 직접 만들었다).

   ```bash
   # link.sh의 # Claude Code 섹션에 추가
   link_file "$DOTFILES_PATH/claude/statusline-command.sh" ~/.claude/statusline-command.sh
   ```

백업(`*.old`)은 동기화가 검증되면 지워도 된다. `.old` 파일은 repo에 commit하지 않는다.

> **link.sh의 역할**: `link.sh`는 **dotfiles를 새 머신에 처음 설치할 때 한 번** 돌리는 부트스트랩
> 스크립트다. 이미 쓰고 있는 머신에서 개별 파일을 새로 관리 대상에 넣을 때는 위 4번처럼 symlink를
> **직접** 만들고, `link.sh`에는 5번처럼 줄만 추가한다. 단일 파일을 링크하려고 `link.sh` 전체를
> 실행하지 않는다(다른 파일까지 건드릴 수 있다).

동기화가 끝나면 `git status`로 의도한 변경만 staged 되는지 다시 확인한다.

#### 임의 경로를 새로 dotfile로 추가하기

사용자가 기존 매핑에 없는 경로를 직접 지정하며 "이 경로를 dotfile로 추가해줘"라고 하는 경우가 있다
(예: `~/.config/ghostty/config`). 이때는 다음과 같이 repo 위치를 정한다:

- 홈 바로 아래의 dotfile(`~/.foo`)이면 → 도구 이름 디렉터리에 점을 떼고 넣는다: `foo/foo` 또는 `foo/config`.
- XDG 스타일(`~/.config/<tool>/<file>`)이면 → repo 최상위에 `<tool>/<file>`로 넣는다.
  예: `~/.config/ghostty/config` → `ghostty/config`, scope는 `ghostty`.

처리 절차는 위 **최초 링크 생성 절차**(백업 → 비교 → 최신화 → 직접 링크 → link.sh 기록)와 같다.
**작업 디렉터리에 무관하게** 절대 경로로 진행한다:

```bash
# REPO는 위 "저장소 경로 찾기"에서 이미 해석된 값
SRC=~/.config/ghostty/config
DST="$REPO/ghostty/config"        # repo 안에서의 위치

[ -e "$SRC" ] && [ ! -L "$SRC" ] && cp -p "$SRC" "$SRC.old"   # 1) 백업
[ -e "$DST" ] && diff "$SRC" "$DST"                           # 2) 비교
mkdir -p "$(dirname "$DST")"; cp "$SRC" "$DST"                # 3) 최신화
ln -sfn "$DST" "$SRC"                                         # 4) 직접 링크
```

그리고 5) `link.sh`에 새 섹션과 `link_file` 한 줄을 **기록**한다. `link_file`은 내부에서 `mkdir -p`로
중첩 디렉터리(`~/.config/ghostty/`)를 알아서 만들어 주므로 XDG 경로도 그대로 쓸 수 있다:

```bash
# Ghostty
link_file "$DOTFILES_PATH/ghostty/config" ~/.config/ghostty/config
```

도구 이름이나 repo 위치가 애매하면 사용자에게 한 번 확인한다.

### 3. commit 한다 (자동)

scope별로 묶어서 commit한다. 이 저장소의 컨벤션은 `[scope] message`이며 scope는 최상위 디렉터리
이름(`claude`, `vim`, `tmux`, `git`, `zsh`, 또는 새로 추가한 `ghostty` 같은 도구 이름)이다.
서로 다른 scope의 변경이 섞였다면 가능하면 **scope별로 나눠서** 여러 commit으로 만든다.
새 도구를 처음 추가하는 경우 `link.sh` 변경은 그 도구 scope에 함께 묶는다.

```bash
git -C "$REPO" add claude/statusline-command.sh claude/settings.json link.sh
git -C "$REPO" commit -m "[claude] add jellybeans statusline and sync settings"
```

메시지는 영어로, 무엇이 왜 바뀌었는지 간결하게 적는다. 최근 로그(`git log --oneline -10`)를 참고해
톤을 맞춘다. commit은 사용자에게 따로 묻지 않고 진행한다.

### 4. push 한다 (반드시 확인)

push는 외부로 나가는 작업이므로 **항상 사용자에게 먼저 확인**한다. 무엇을 push할지 요약해서 보여준다:

```bash
git -C "$REPO" log origin/main..HEAD --oneline   # push될 커밋 미리보기
```

사용자가 동의하면 `git push`, 보류하면 commit 상태로 남겨 둔다. 사용자가 처음부터 "push까지 해줘"라고
명시했다면 그 한 번의 요청을 동의로 보고 바로 push해도 된다.

## 주의

- repo 경로 매핑은 외우지 말고 매번 `link.sh`에서 읽는다. 매핑이 바뀌어 있을 수 있다.
- drift된 파일을 repo로 동기화할 때 어느 쪽이 최신인지 확신이 없으면 덮어쓰기 전에 `diff`를 보여주고
  확인한다. 사용자가 손으로 repo를 고쳤을 가능성도 있다.
- `.gitkeep` 같은 placeholder 파일은 건드리지 않는다.
- 비밀값(토큰, 키, 쿠키 파일 등)이 새로 추적되려는지 확인한다. 의심되면 commit 전에 알린다.
- 이 스킬은 dotfiles 저장소에만 적용된다. Obsidian vault 등 다른 저장소에는 적용하지 않는다.

## 날짜 / 환경 확인

필요하면 `date`, `git remote -v`, `git branch --show-current` 등으로 현재 환경을 확인한다.
원격은 보통 `origin git@github.com:<you>/dotfiles.git` 형태이고, 기본 브랜치는 보통 `main`이다.
실제 값은 위 명령으로 확인한다.
