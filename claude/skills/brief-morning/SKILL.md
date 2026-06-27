---
name: brief-morning
description: |
  아침 업무 시작 루틴: 이날의 기록·지난 일지 요약, 이번 주 일정, 받은편지함 요약, 로컬 git 상태, PR 현황을 한 번에 모아 브리핑한다.
  트리거: "아침 브리핑", "모닝 브리핑", "morning brief", "업무 시작", "/brief-morning" 등.
  config.yaml이 없으면 사용자에게 설정을 묻고 파일을 생성한 뒤 작업을 진행한다.
---

# Brief Morning

아침 업무 시작 루틴: 어제(또는 최근) 작업 요약 및 오늘 챙길 것들을 한 화면에 모은다.

## 제약사항

- **정보 수집 및 요약만 진행** — 읽기 전용 작업이 원칙. vault나 repo를 수정하지 않는다.
- 단, `config.yaml`이 존재하지 않는 경우에 한해 **최초 1회 설정 파일 생성**은 허용한다.

---

## STEP 0: 설정 읽기 (가장 먼저 실행)

스킬 디렉터리의 `config.yaml`을 읽어 이 머신의 설정을 파악한다.

```bash
cat ~/.claude/skills/brief-morning/config.yaml 2>/dev/null || echo "NO_CONFIG"
```

### config.yaml이 있는 경우

파일 내용을 파싱하여 설정값을 확인하고, **enabled된 태스크만** 아래 병렬 실행 블록에서 수행한다.

### config.yaml이 없는 경우 (NO_CONFIG)

`AskUserQuestion` tool로 사용자에게 직접 물어본다. 질문은 **한 번에 모두** 묻는다(여러 번 나눠서 묻지 않는다):

**질문 1** — 수행할 작업 선택 (multiSelect: true)
- `on_this_day` — 이날의 기록 (과거 같은 날짜의 daily note)
- `calendar` — Google Calendar 이번 주 일정 (Calendar MCP)
- `gmail` — Gmail 받은편지함 요약 (Gmail MCP)
- `daily_note` — 최신 daily note 확인
- `git_status` — Git 로컬 상태 확인
- `github_pr` — GitHub PR 조회 (`gh` CLI 필요)

**질문 2** — `git_status`를 선택한 경우: 작업 베이스 디렉터리 (이 아래 git repo들을 자동 탐색)
- 예시 옵션: `~/Workspace/github`, `~/Workspace` + "직접 입력". `recent_days`는 기본 30.

**질문 3** — `github_pr`를 선택한 경우: PR 조회할 저장소 목록 (쉼표 구분, 예: `owner/repo`)

> ⚠️ `git_status`나 `github_pr`를 선택하지 않았다면 해당 질문은 건너뛴다.
> ⚠️ `github_pr`는 `gh` CLI가 필요하다. 미설치면 `brew install gh && gh auth login` 안내 후 기본 off로 둔다.

### config.yaml 생성

사용자 응답을 바탕으로 `~/.claude/skills/brief-morning/config.yaml`을 **Write tool**로 생성한다. 형식은 `config.example.yaml`을 따른다. 생성 후 안내한다:

```
✅ config.yaml이 생성되었습니다: ~/.claude/skills/brief-morning/config.yaml
다음 실행부터는 자동으로 이 설정을 사용합니다.
```

---

## 실행 전략

**Agent 기반 병렬 실행**: enabled된 작업 그룹은 서로 독립적이므로 **Agent tool로 동시에 실행**한다.

```
┌─────────────────────────────────────────────────────────────────┐
│                     메인 컨텍스트 (직접 실행)                     │
│  TASK A (이날의 기록) + TASK E (최신 일지)                        │
│  → 로컬 파일 읽기만 하므로 Agent 없이 직접 처리                  │
│  → 파일 탐색은 단일 Bash 호출로 A + E를 동시 수행               │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────────────┬──────────────────────────┐
│   Agent 1 (sonnet)       │   Agent 2 (sonnet)       │
│  TASK B + C              │  TASK F + G              │
│  (일정 + 메일, MCP)      │  (Git 상태 + GitHub PR)  │
└──────────────────────────┴──────────────────────────┘
```

### 실행 방법

1. **메인 컨텍스트**: TASK A + E 파일 탐색을 **단일 Bash 호출**로 동시 수행 → 찾은 파일을 **Read 병렬 호출**로 한 번에 읽는다.
2. **Agent 병렬 실행**: 나머지 enabled된 그룹을 **하나의 메시지에서 2개 Agent 동시 호출**.
   - **Agent 1** (`model: "sonnet"`): Calendar + Gmail — **MCP 도구**로 수집·요약.
   - **Agent 2** (`model: "sonnet"`): Git 상태 + GitHub PR — 동일 CLI 기반, Bash `&`로 병렬.
   - 두 Agent 결과를 취합하여 최종 출력 생성.

> ⚠️ **반드시 하나의 메시지에서 2개 Agent를 동시 호출**해야 진정한 병렬 실행이 된다. 순차 호출 금지.
> ⚡ 두 Agent 모두 데이터 수집+포맷팅만 하므로 `model: "sonnet"`으로 응답 속도를 높인다.

---

## TASK A: 이날의 기록 (On This Day)

> **건너뛰기 조건**: `tasks.on_this_day: false`

오늘과 **같은 월-일(MM-DD)** 의 과거 연도 daily note를 모두 조회한다. 내 vault는 daily note가 **단일 폴더 평면 구조**(`Retrospective/1. Daily/YYYY-MM-DD.md`, 연도 폴더 없음)이므로 파일명 기준으로 글롭한다.

> ⚡ TASK E(최신 일지)의 파일 탐색과 **단일 Bash 호출로 동시 수행**한다.

```bash
# 매칭 없는 글로브를 빈 목록으로 (zsh/bash 공통) — 과거 기록이 없을 때 에러 방지
setopt null_glob 2>/dev/null; shopt -s nullglob 2>/dev/null

VAULT="/Users/amoseui/Obsidian/amoseui/Retrospective/1. Daily"
TODAY_MMDD=$(date '+%m-%d')
CUR_YEAR=$(date '+%Y')

# === A: On This Day (과거 같은 날짜, 평면 폴더) ===
echo "=== ON_THIS_DAY ==="
for f in "$VAULT"/*-"$TODAY_MMDD".md; do
  [ -f "$f" ] || continue
  y=$(basename "$f" | cut -c1-4)
  [ "$y" = "$CUR_YEAR" ] && continue   # 올해는 제외
  echo "$f"
done | sort

# === E: 최신 daily note (오늘 제외, 주말이면 금~일 묶기) ===
echo "=== LATEST_DAILY ==="
LATEST=""
for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14; do
  D=$(date -v-${i}d '+%Y-%m-%d')
  [ -f "$VAULT/$D.md" ] && LATEST="$D" && break
done
if [ -n "$LATEST" ]; then
  DOW=$(date -j -f '%Y-%m-%d' "$LATEST" '+%w')
  if [ "$DOW" = "0" ] || [ "$DOW" = "6" ]; then
    COLLECT="$LATEST"
    for extra in 1 2; do
      D_PREV=$(date -j -f '%Y-%m-%d' -v-${extra}d "$LATEST" '+%Y-%m-%d')
      DOW_PREV=$(date -j -f '%Y-%m-%d' "$D_PREV" '+%w')
      [ -f "$VAULT/$D_PREV.md" ] && COLLECT="$D_PREV $COLLECT"
      [ "$DOW_PREV" = "5" ] && break
    done
    echo "$COLLECT"
  else
    echo "$LATEST"
  fi
fi
```

- `=== ON_THIS_DAY ===` 이후 줄들이 A의 파일 목록, `=== LATEST_DAILY ===` 이후 줄이 E의 날짜 목록.
- 이 결과를 파싱한 뒤 모든 파일을 **Read tool 병렬 호출**로 한 번에 읽는다.
- 각 파일에서 핵심 내용을 **1~2줄로 간략 요약**(주요 이벤트·완료 작업·특이사항). 의미 있는 기록이 없으면 해당 연도 생략.

---

## TASK B+C: Google Calendar + Gmail (Agent 1, `model: "sonnet"`)

> **건너뛰기 조건**: `tasks.calendar: false` AND `tasks.gmail: false` 둘 다 false면 이 Agent 생략.

친구 dotfiles는 google-*-improved 스킬 스크립트를 썼지만, 이 머신은 **Calendar/Gmail MCP**가 연결돼 있으므로 MCP 도구로 수집한다.

### Calendar (MCP)

- `Google_Calendar` MCP의 `list_events`로 **오늘부터 7일** 범위 일정을 조회한다(필요하면 `list_calendars`로 캘린더 목록 확인).
- 날짜별 그룹핑, 시간순 정렬. 오늘 일정은 **굵게** 강조. 일정 없는 날은 생략.
- 여러 캘린더가 있으면 캘린더별로 🔵/🟢 등으로 구분, 같은 시간대 충돌은 ⚠️ 표시.

### Gmail (MCP)

- `Gmail` MCP의 `search_threads`로 `in:inbox newer_than:10d` 최근 받은편지함(최대 ~20개)을 조회한다.
- 발신자 / 제목 / 수신 시각을 **표 형식**으로 정리. 본문은 읽지 않고 제목·발신자로만 요약.
- 공지·리뷰 요청·긴급 등 중요해 보이는 메일은 ⚠️ 표시. 메일이 없으면 "받은편지함 메일 없음".

---

## TASK E: 최신 Daily Note 확인

> **건너뛰기 조건**: `tasks.daily_note: false`
> ⚡ 파일 탐색은 TASK A의 통합 Bash에서 이미 수행됨. `=== LATEST_DAILY ===` 결과를 사용.

오늘을 제외한 가장 최신 daily note를 읽는다. 주말(토·일)이 포함되면 금요일까지 함께 읽는다.

- 수집된 날짜의 각 파일을 **TASK A 파일들과 함께 Read 병렬 호출**로 읽어 요약.
- 추출 정보: 완료한 작업, 진행 중인 작업, TODO. 파일이 하나도 없으면 섹션 생략.
- 출력: 평일이면 `## 지난 일지 요약 (YYYY-MM-DD)`, 주말 포함이면 `## 지난 일지 요약 (금 YYYY-MM-DD ~ 일 YYYY-MM-DD)`로 날짜 범위 명시하고 날짜별 `### YYYY-MM-DD (요일)`로 구분.

---

## TASK F+G: Git 상태 + GitHub PR (Agent 2, `model: "sonnet"`)

> **건너뛰기 조건**: `tasks.git_status: false` AND `tasks.github_pr: false` 둘 다 false면 이 Agent 생략.

### F: Git 로컬 상태 확인

`config.yaml`의 `git.workspace` 아래에서 **최근 `git.recent_days`일 내 커밋이 있는 git repo를 자동 탐색**한 뒤 각 repo의 worktree 상태를 확인한다.

- 탐색 범위: `git.workspace` 최상위 + 그룹 폴더 한 단계 하위(repo 내부로는 안 들어감).
- 활동 신호: 마지막 커밋 시각이 `recent_days`일 이내.
- 제외: `git.exclude` 목록의 repo 디렉터리명.

```bash
setopt null_glob 2>/dev/null; shopt -s nullglob 2>/dev/null

WORKSPACE="/Users/amoseui/Workspace/github"   # config: git.workspace
RECENT_DAYS=30                                  # config: git.recent_days
EXCLUDE=()                                       # config: git.exclude

CUTOFF=$(( $(date +%s) - RECENT_DAYS * 86400 ))

CANDIDATES=()
for d1 in "$WORKSPACE"/*/; do
  if [ -e "${d1}.git" ]; then
    CANDIDATES+=("${d1%/}")
  else
    for d2 in "$d1"*/; do
      [ -e "${d2}.git" ] && CANDIDATES+=("${d2%/}")
    done
  fi
done

RECENT_REPOS=()
for repo in "${CANDIDATES[@]}"; do
  name=$(basename "$repo")
  skip=""
  for ex in "${EXCLUDE[@]}"; do [ "$name" = "$ex" ] && skip=1; done
  [ -n "$skip" ] && continue
  ts=$(git -C "$repo" log -1 --format=%ct 2>/dev/null) || continue
  [ -n "$ts" ] && [ "$ts" -ge "$CUTOFF" ] && RECENT_REPOS+=("$repo")
done
echo "SCANNED_RECENT_REPOS: ${#RECENT_REPOS[@]} (최근 ${RECENT_DAYS}일 내 커밋)"

for repo in "${RECENT_REPOS[@]}"; do
  while IFS= read -r wt; do
    [ -n "$wt" ] || continue
    (
      echo "=== $wt ==="
      cd "$wt" && \
      echo "BRANCH: $(git branch --show-current)" && \
      echo "STATUS:" && git status --porcelain && \
      echo "UNPUSHED:" && (git log @{u}..HEAD --oneline 2>/dev/null || echo "(no upstream)")
    ) &
  done < <(git -C "$repo" worktree list --porcelain | awk '/^worktree /{print $2}')
done
wait

# superpowers plan(진행 중 작업 계획) 신호 — 읽기 전용, 파일 존재만 확인
for repo in "${RECENT_REPOS[@]}"; do
  for p in "$repo"/docs/superpowers/plans/*.md; do
    [ -f "$p" ] && echo "PLAN: $(basename "$repo") :: $(basename "$p")"
  done
done
```

**보고 기준**: 미커밋 변경(STATUS) 또는 미푸시 커밋(UNPUSHED)이 **하나라도 있는 worktree만** 표에 표시. 완전히 깨끗한 worktree는 생략하고 스캔한 repo 개수만 적는다. pending이 전혀 없으면 "정리 안 된 로컬 작업 없음".

**진행 중 작업(superpowers plan) 신호**: `PLAN:` 줄이 있으면 해당 repo에 `docs/superpowers/plans/`(writing-plans 구현 계획)가 남아 있다는 뜻이므로 "진행 중인 작업 계획"으로 함께 표시한다. plan **파일명만** 가볍게 나열하고 본문은 읽지 않는다(읽기 전용 유지). gitignore된 로컬 산출물이라 없을 수 있으니 없으면 생략.

### G: GitHub PR 조회

> **건너뛰기 조건**: `tasks.github_pr: false` 또는 `github.repos`가 비어 있음. `gh` 미설치면 생략하고 설치 안내.

`config.yaml`의 `github.repos` 배열을 모두 **하나의 Bash에서 `&`로 병렬**:

```bash
REPOS=()   # config: github.repos (예: "owner/repo")
command -v gh >/dev/null 2>&1 || { echo "GH_NOT_INSTALLED"; exit 0; }
for repo in "${REPOS[@]}"; do
  (
    echo "=== $repo - MY PRS ==="
    gh pr list --author @me --repo "$repo" --state open \
      --json number,title,reviewDecision,mergeable,statusCheckRollup 2>&1
    echo "=== $repo - REVIEW NEEDED ==="
    gh pr list --repo "$repo" --state open --json number,title,author 2>&1
  ) &
done
wait
```

G 결과에서 내가 작성한 PR(`author.login == @me`)은 "리뷰 대기"에서 제외.

---

## 출력 형식

enabled된 섹션만 출력하고 disabled된 섹션은 완전히 생략한다.

```markdown
# 🌅 Morning Brief - YYYY-MM-DD

## 📅 이날의 기록 (On This Day)
> 과거 같은 날짜(MM-DD)의 기록을 돌아봅니다.

- **YYYY년** — [1~2줄 요약]

_(해당 날짜의 기록이 없으면 이 섹션 생략)_

## 🗓️ 일정

### MM/DD (요일) — 오늘
- [HH:MM-HH:MM] 일정 제목

### MM/DD (요일)
- [HH:MM-HH:MM] 일정 제목

_(일정 없는 날은 생략, 충돌 시 ⚠️ 표시)_

## 📬 받은편지함 메일 요약
| 발신자 | 제목 | 수신 시각 |
|--------|------|-----------|
| ... | ... | ... |

_(메일이 없으면 "받은편지함 메일 없음")_

## 지난 일지 요약
[요약 내용]

## 오늘 해야 할 일
[daily note에서 추출한 TODO 항목]

## 💻 로컬 작업 현황
> 최근 N일 내 활동 repo M개 스캔 (~/Workspace/github 자동 탐색)

| 경로 | 브랜치 | 미커밋 변경 | 미푸시 커밋 |
|------|--------|-------------|-------------|

_(미커밋·미푸시가 있는 worktree만 표시. 전부 깨끗하면 "정리 안 된 로컬 작업 없음")_

**📋 진행 중인 작업 계획** _(superpowers plan이 있을 때만)_
- {repo}: {plan 파일명}

## 📤 내 PR 현황
- 총 N개의 열린 PR (🟢 머지 가능 / 🟡 리뷰 대기 / 🔴 조치 필요)

### {repo_name}
| PR | 제목 | 리뷰 상태 | 머지 가능 | CI |
|----|------|-----------|-----------|-----|

## 📥 PR 리뷰 대기
### {repo_name}
| PR | 제목 | 작성자 |
|----|------|--------|
```

## 날짜 / 환경 확인

오늘 날짜·요일은 `date`로 확인한다(시간대 Asia/Seoul, KST). vault 경로에 공백이 있으므로(`Retrospective/1. Daily`) Glob tool 대신 항상 Bash로 파일을 탐색한다.
