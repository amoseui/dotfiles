---
name: brief-morning
description: |
  아침 업무 시작 루틴(읽기 전용 브리핑): 이날의 기록(과거 같은 날짜), 지난 일지 요약,
  이번 주 캘린더 일정, 별표/받은편지함 메일 요약, 오늘 Todoist 할 일, 로컬 git 상태,
  GitHub PR 현황을 한 번에 모아 브리핑한다. vault나 repo를 수정하지 않는다.
  트리거: "아침 브리핑", "모닝 브리핑", "morning brief", "업무 시작", "오늘 뭐부터".
version: 1.0.0
author: Hermes Agent + Amos
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [briefing, morning, calendar, gmail, git, github, todoist]
    category: note-taking
    related_skills: [daily-notes-automation, google-workspace, hermes]
---

# Brief Morning (읽기 전용 아침 브리핑)

어제(또는 최근) 작업 요약 + 오늘 챙길 것들을 한 화면에 모은다. **정보 수집·요약만** 하고
vault·repo를 수정하지 않는다(daily note를 채우는 건 daily-notes-automation cron의 몫).

## 0. 고정 환경

> 개인 식별 값(vault/workspace 경로, 계정 id, github user)은 **`hermes` 스킬의 `config.yaml`**에만
> 둔다. 셸에서는 한 줄로 로드해 `$CFG_*` 변수로 쓴다:
> `eval "$(python3 ~/.hermes/skills/note-taking/daily-notes-automation/scripts/_config.py --shell)"`

| 항목 | 값 |
|------|----|
| Vault 루트 | `$CFG_vault_path` (config) |
| daily note | `{vault}/Retrospective/1. Daily/YYYY-MM-DD.md` (연도 폴더 없는 평면 구조) |
| Git workspace | `$CFG_git_workspace` (config, recent_days=30) |
| 캘린더 | PRIMARY 계정 `$CFG_accounts_primary` (scripts via daily-notes-automation) |
| 메일 | PRIMARY+SECOND 별표 + 받은편지함 |
| 스킬 스크립트 | daily-notes-automation/scripts/{calendar_today,starred_mail}.py |
| 타임존 | Asia/Seoul (KST) — `TZ=Asia/Seoul date` |

원하는 섹션만 켜고 끄려면 사용자에게 묻되, 기본은 전부 수행한다.

## 실행 전략

읽기 전용이므로 빠르게 병렬화한다. 독립적인 무거운 수집(메일/캘린더/PR)은 `delegate_task`로
동시에 돌리거나, 가벼우면 한 턴에 여러 도구를 병렬 호출한다. 로컬 파일 읽기(이날의 기록 +
최신 일지)는 단일 terminal 호출로 파일 목록을 뽑고 read_file 병렬로 읽는다.

## TASK A: 이날의 기록 (On This Day)

오늘과 **같은 월-일(MM-DD)** 의 과거 연도 daily note를 모두 조회(평면 폴더, 파일명 글롭).
TASK E와 단일 terminal 호출로 동시 수행:
```bash
eval "$(python3 ~/.hermes/skills/note-taking/daily-notes-automation/scripts/_config.py --shell)"
setopt null_glob 2>/dev/null; shopt -s nullglob 2>/dev/null
VAULT="$CFG_vault_path/Retrospective/1. Daily"
TODAY_MMDD=$(TZ=Asia/Seoul date '+%m-%d'); CUR_YEAR=$(TZ=Asia/Seoul date '+%Y')
echo "=== ON_THIS_DAY ==="
for f in "$VAULT"/*-"$TODAY_MMDD".md; do
  [ -f "$f" ] || continue
  y=$(basename "$f" | cut -c1-4); [ "$y" = "$CUR_YEAR" ] && continue
  echo "$f"
done | sort
echo "=== LATEST_DAILY ==="
for i in $(seq 1 14); do
  D=$(TZ=Asia/Seoul date -v-${i}d '+%Y-%m-%d')
  [ -f "$VAULT/$D.md" ] && echo "$D" && break
done
```
- `ON_THIS_DAY` 파일들을 read_file 병렬로 읽어 각 연도 1~2줄 요약. 없으면 섹션 생략.

## TASK E: 최신 Daily Note
- `LATEST_DAILY` 날짜 파일을 read_file로 읽어 완료한 작업/진행 중/TODO 추출 요약.

## TASK B: 캘린더 (PRIMARY)
```bash
python3 ~/.hermes/skills/note-taking/daily-notes-automation/scripts/calendar_today.py
```
오늘 일정. 이번 주 전체를 원하면 google_api.py를 PRIMARY HERMES_HOME으로 직접 호출:
```bash
eval "$(python3 ~/.hermes/skills/note-taking/daily-notes-automation/scripts/_config.py --shell)"
HERMES_HOME=~/.hermes/google-accounts/$CFG_accounts_primary python3 \
  ~/.hermes/skills/productivity/google-workspace/scripts/google_api.py calendar list \
  --start "$(TZ=Asia/Seoul date +%Y-%m-%d)T00:00:00+09:00" \
  --end "$(TZ=Asia/Seoul date -v+7d +%Y-%m-%d)T23:59:59+09:00"
```
날짜별 그룹핑·시간순. 오늘 일정 강조. 일정 없는 날 생략.

## TASK C: 메일 (별표 + 받은편지함)
```bash
eval "$(python3 ~/.hermes/skills/note-taking/daily-notes-automation/scripts/_config.py --shell)"
# 별표(두 계정 합침)
python3 ~/.hermes/skills/note-taking/daily-notes-automation/scripts/starred_mail.py
# 받은편지함 최근(계정별)
for A in "$CFG_accounts_primary" "$CFG_accounts_second"; do
  HERMES_HOME=~/.hermes/google-accounts/$A python3 \
    ~/.hermes/skills/productivity/google-workspace/scripts/google_api.py \
    gmail search "in:inbox newer_than:3d" --max 15
done
```
발신자/제목/시각 표로. 본문 안 읽음. 중요(공지·리뷰·긴급)는 ⚠️. 없으면 "메일 없음".

## TASK D: 오늘 Todoist 할 일
Todoist MCP `todoist_task_get` filter `(today | overdue) & p1`. 각 항목 `* 내용`. 없으면 "오늘 p1 없음".
(MCP는 새 세션에서만 보임 — 안 보이면 이 섹션 생략.)

## TASK F: Git 로컬 상태
config의 `git_workspace` 아래 최근 30일 내 커밋 있는 repo를 탐색해 worktree 상태 확인:
```bash
eval "$(python3 ~/.hermes/skills/note-taking/daily-notes-automation/scripts/_config.py --shell)"
setopt null_glob 2>/dev/null; shopt -s nullglob 2>/dev/null
WORKSPACE="$CFG_git_workspace"; RECENT_DAYS=30
CUTOFF=$(( $(date +%s) - RECENT_DAYS*86400 ))
CANDIDATES=()
for d1 in "$WORKSPACE"/*/; do
  if [ -e "${d1}.git" ]; then CANDIDATES+=("${d1%/}")
  else for d2 in "$d1"*/; do [ -e "${d2}.git" ] && CANDIDATES+=("${d2%/}"); done; fi
done
for repo in "${CANDIDATES[@]}"; do
  ts=$(git -C "$repo" log -1 --format=%ct 2>/dev/null) || continue
  [ "$ts" -ge "$CUTOFF" ] || continue
  cd "$repo" || continue
  st=$(git status --porcelain); up=$(git log @{u}..HEAD --oneline 2>/dev/null)
  [ -n "$st$up" ] && { echo "=== $repo ($(git branch --show-current)) ==="; [ -n "$st" ] && echo "$st"; [ -n "$up" ] && echo "UNPUSHED:" && echo "$up"; }
done
```
미커밋/미푸시 있는 worktree만 표로. 전부 깨끗하면 "정리 안 된 로컬 작업 없음".

## TASK G: GitHub PR (gh)
`gh`가 인증돼 있으면 관심 repo의 내 PR + 리뷰 대기 조회:
```bash
gh pr list --author @me --state open --json number,title,reviewDecision,repository 2>/dev/null
```
내 PR(머지가능/리뷰대기/조치필요)과 리뷰 대기를 구분. repos를 모르면 최근 활동 repo 기준.

## 출력 형식
```markdown
# 🌅 Morning Brief - YYYY-MM-DD
## 📅 이날의 기록
- **YYYY년** — [1~2줄]
## 🗓️ 일정
### MM/DD (요일) — 오늘
- [HH:MM-HH:MM] 제목
## 📬 메일
| 발신자 | 제목 | 시각 |
## ✅ 오늘 할 일 (p1)
- 내용
## 지난 일지 요약
[요약]
## 💻 로컬 작업 현황
| 경로 | 브랜치 | 미커밋 | 미푸시 |
## 📤 PR 현황
- ...
```
enabled 섹션만 출력, 비어있으면 해당 섹션 생략.

## Pitfalls
- **읽기 전용** — vault/repo 수정 금지. daily note는 daily-notes-automation cron이 채운다.
- 시각은 `TZ=Asia/Seoul date`. vault 경로 공백(`1. Daily`) 주의 → Glob 대신 terminal.
- Todoist MCP는 새 세션에서만 보임.
- 캘린더=PRIMARY, 메일=PRIMARY+SECOND(계정 id는 config). gh는 별도 로그인 계정 사용.

## 의존성
- `read_file` / `search_files` / `terminal` / (선택) `delegate_task`
- daily-notes-automation/scripts (calendar_today, starred_mail) + google-workspace/google_api.py
- Todoist MCP (선택), `gh` CLI (선택)
