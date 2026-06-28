---
name: daily-notes-automation
description: |
  Obsidian daily note(회고) 자동 생성·채움 cron 작업용 스킬 (Hermes 전용).
  매일 아침(06:00) 일일 회고 노트를 템플릿으로 생성하고 캘린더/Todoist/별표메일로 채우며,
  매일 밤(23:50) Git 커밋·캘린더 지난 일정·Todoist 완료 항목으로 일일 회고 섹션을 채운다.
  검증된 헬퍼 스크립트(scripts/)와 계정/경로가 박제돼 있어 cron이 헤매지 않는다.
  트리거: daily note 자동화, 아침 브리핑, 밤 회고, 회고 노트 cron, 이 스킬을 로드하는 cron 작업.
version: 1.0.0
author: Hermes Agent + Amos
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [obsidian, daily-note, cron, retrospective, briefing, automation]
    category: note-taking
    related_skills: [hermes, google-workspace]
---

# Daily Notes Automation — 아침 브리핑 + 밤 회고

매일 정해진 시각에 Obsidian의 일일 회고 노트(`Retrospective/1. Daily/YYYY-MM-DD.md`)를
자동으로 만들고 외부 데이터로 채우는 **cron 작업 전용** 스킬이다.
사람이 직접 호출하기보다 cron job이 이 스킬을 로드해 절차를 그대로 수행한다.

> 이 스킬은 `hermes` PKM 스킬의 **변경 이력 규칙**(노트 하단 `## History` +
> `wiki/log.md` 통합 로그)을 그대로 따른다. vault 경로/규칙이 헷갈리면 `hermes` 스킬과
> 그 `config.yaml`을 기준으로 삼는다.

## 0. 고정 환경 (검증 완료 — 추측 금지)

| 항목 | 값 |
|------|----|
| Vault 루트 | `/Users/amoseui/Obsidian/amoseui/amoseui` |
| 일일 노트 | `{vault}/Retrospective/1. Daily/YYYY-MM-DD.md` |
| 템플릿 | `{vault}/Templates/template-retrospective-1-daily.md` |
| 통합 로그 | `{vault}/wiki/log.md` (헤딩 `# Change Log`, 최신이 맨 위) |
| 타임존 | Asia/Seoul (KST) — 날짜/시각은 항상 `TZ=Asia/Seoul date` |
| 스킬 스크립트 | `~/.hermes/skills/note-taking/daily-notes-automation/scripts/` |

### 데이터 소스 (계정 매핑 — 사용자 확정)

| 데이터 | 소스 | 방법 |
|--------|------|------|
| 오늘 일정 / 지난 일정 | **prenine** 캘린더 | `scripts/calendar_today.py` |
| 할 일 (오늘+기한지남 p1) | **Todoist** (MCP) | `todoist_*` 도구, filter `(today \| overdue) & p1` |
| 별표 메일 (전체) | **amoseui + prenine** 합침 | `scripts/starred_mail.py` |
| Git 커밋 | **amoseui** GitHub | `scripts/git_commits_today.py` (atom 피드, 인증 불필요) |
| Todoist 완료 항목 | **Todoist** (MCP) | `todoist_activity_by_date_range` (recurring 포함) |

> Google 토큰은 계정별로 `~/.hermes/google-accounts/{amoseui,prenine}/google_token.json`에
> 분리 저장돼 있다. 헬퍼 스크립트가 `HERMES_HOME`을 바꿔가며 계정을 전환하므로
> cron 프롬프트는 스크립트만 호출하면 된다. amoseui는 Calendar 미사용(Gmail만), prenine은 둘 다.

## 0.1 헬퍼 스크립트 (이미 검증됨)

전부 KST 기준, 마크다운 bullet(`* …`)로 출력하며 데이터 없으면 "…없음" 한 줄을 낸다.
**대괄호 `[ ]`는 출력 단계에서 `( )`로 치환**한다(daily note 규칙: 대괄호 금지).

```bash
SC=~/.hermes/skills/note-taking/daily-notes-automation/scripts
python3 "$SC/calendar_today.py"      # * HH:MM-HH:MM 제목  /  * 오늘 일정 없음
python3 "$SC/starred_mail.py"        # * (발신자) 제목  /  * 새로운 중요 메일 없음
python3 "$SC/git_commits_today.py"   # * repo: 커밋메시지  /  * 오늘 커밋 없음
```

각 스크립트는 선택적 `YYYY-MM-DD` 인자(특정 날짜)를 받는다(calendar/git). 인자 없으면 오늘(KST).

> ⚠️ **수동 검증 시 python 버전 주의**: calendar/starred 스크립트는 내부에서 `google_api.py`(Python 3.10+ 전용)를 `sys.executable`로 부른다. cron은 venv python(3.11)으로 돌아 OK지만, 터미널에서 직접 테스트할 때 시스템 `python3`(3.9)로 스크립트를 부르면 google_api.py가 import 단계에서 죽어 거짓 "…없음"이 나온다. 직접 검증은 반드시 `~/.hermes/hermes-agent/venv/bin/python "$SC/..."` 로 한다(Pitfalls 참고).

## 0.2 Todoist (MCP 도구 — cron 새 세션에서 사용)

Todoist는 Hermes MCP(`mcp-todoist`)로 연결돼 있고 **새 세션부터** 도구가 뜬다(cron은 항상 새 세션).

- **할 일 (아침)**: `todoist_task_get` 으로 filter `(today | overdue) & p1` 조회.
  - Todoist 우선순위는 API에서 p1=`priority:4`(가장 높음)다. 도구가 `priority` 인자를 받으면 최고 우선순위를 쓰고,
    filter 문자열을 받으면 `"(today | overdue) & p1"`을 그대로 넘긴다.
  - 각 항목 → `* 태스크 내용`. 없으면 `* 오늘 p1 할 일 없음`.
- **완료 항목 (밤)**: `todoist_completed_tasks_get`은 **recurring 완료를 누락**한다 →
  반드시 `todoist_activity_by_date_range` 사용.
  - `since`: 오늘 KST 00:00 = 전날 `T15:00:00Z`, `until`: 오늘 KST 23:59 = 당일 `T14:59:59Z`,
    `event_type: "completed"`, `object_type: "item"`.
  - 반환값을 KST로 변환해 **오늘 날짜 항목만** 필터, `extra.content`에서 제목 추출, 중복 제거.
  - 각 항목 → `* 작업 제목`. 없으면 `* 오늘 완료 항목 없음`.

도구가 안 보이면(연결 끊김 등) 해당 섹션은 "…없음"으로 채우고 계속 진행한다(작업 중단 금지).

---

## 작업 A — 아침 통합 (06:00): 노트 생성 + 브리핑 채움

> 작업 1(템플릿 생성)과 작업 2(아침 브리핑)를 **하나로 합친** 절차다.

### A-1. 날짜 확인
```bash
TZ=Asia/Seoul date +"%Y-%m-%d %H:%M"   # → DATE, TIME
```

### A-2. 노트 존재 확인 / 생성
- 대상: `{vault}/Retrospective/1. Daily/{DATE}.md`
- **이미 있으면** 새로 만들지 않고(절대 덮어쓰지 않음) 기존 파일을 그대로 쓴다(아래 채움 단계로).
- **없으면** 템플릿으로 생성:
  1. `{vault}/Templates/template-retrospective-1-daily.md` 를 `read_file`.
  2. **마지막 `---` 이후 `## History` 섹션은 제외**하고 본문만 복사해 새 파일로 `write_file`.
  3. 폴더(`Retrospective/1. Daily/`)가 없으면 write_file이 자동 생성한다.
  4. 새 파일이므로 본문 끝에 `## History`를 새로 만들고 첫 항목:
     `- {DATE} {TIME} 일일 회고 노트 자동 생성` (변경 이력 규칙은 아래 공통 절차).
  5. 통합 로그에도 기록: `- {DATE} \`Retrospective/1. Daily/{DATE}.md\` — 일일 회고 노트 자동 생성`.

### A-3. 데이터 수집 (병렬로 한 번에)
```bash
SC=~/.hermes/skills/note-taking/daily-notes-automation/scripts
python3 "$SC/calendar_today.py"     # 오늘 일정
python3 "$SC/starred_mail.py"       # 별표 메일 합침
```
+ Todoist `todoist_task_get` filter `(today | overdue) & p1` (0.2 참고).

### A-4. 아침 브리핑 섹션 채움 (`patch`로 bullet만 교체)
파일 상단 구조:
```
## 🌅 아침 브리핑
> 이 섹션은 Claude가 자동으로 채웁니다.
### 오늘 일정
* …            ← 캘린더 결과로 교체
### 오늘 할 일 (Todoist)
* …            ← Todoist p1 결과로 교체
### 이메일/Readwise 요약
* …            ← 별표 메일 결과로 교체
---
```
- 각 헤딩 **바로 아래의 `* ` bullet 라인만** 교체한다. 다른 줄/구조는 절대 건드리지 않는다.
- 헤딩 사이에 기존 bullet이 여러 줄이면 그 블록 전체를 새 bullet들로 치환.
- 대괄호 `[ ]` 금지(스크립트가 이미 치환). 위키링크/마크다운 링크 금지, 순수 텍스트만.

### A-5. 변경 이력 기록 → "공통: 변경 이력" 절차 수행 (action="아침 브리핑 자동 업데이트 (캘린더 일정, Todoist p1, 별표 메일)").

---

## 작업 B — 밤 회고 (23:50): 일일 회고 섹션 채움

### B-1. 날짜/파일 확인
```bash
TZ=Asia/Seoul date +"%Y-%m-%d %H:%M"
```
- `{vault}/Retrospective/1. Daily/{DATE}.md` 를 `read_file`.
- **파일이 없으면 작업 중단**(아침에 생성됐어야 함). 단, cron 안정성을 위해 없으면 작업 A의 생성 단계를 먼저 수행한 뒤 진행해도 된다.

### B-2. 데이터 수집
```bash
SC=~/.hermes/skills/note-taking/daily-notes-automation/scripts
python3 "$SC/git_commits_today.py"   # Git 커밋
python3 "$SC/calendar_today.py"      # 캘린더 지난 일정 (오늘 일정과 동일 소스)
```
+ Todoist 완료 항목: `todoist_activity_by_date_range` (0.2 참고).

### B-3. 일일 회고 섹션 채움 (`patch`로 bullet만 교체)
```
## 🌙 일일 회고
> 이 섹션은 Claude가 자동으로 채웁니다. (매일 밤 …)
### Git 커밋
* …            ← git_commits_today.py 결과
### Todoist 완료 항목
* …            ← todoist_activity_by_date_range 결과 (* 작업 제목)
### 캘린더 지난 일정
* …            ← calendar_today.py 결과 (* HH:MM 제목)
### YouTube 시청 기록
* …            ← 손대지 않음 (소스 없음)
---
```
- 각 헤딩 아래 `* ` bullet만 교체. `YouTube 시청 기록`은 비워둔다(소스 없음).
- 대괄호 `[ ]` 절대 금지. 링크 필요 시 URL을 괄호 없이 평문으로.

### B-4. 변경 이력 기록 → "공통: 변경 이력" 절차 (action="일일 회고 자동 업데이트 (Git 커밋, Todoist 완료 항목, 캘린더 지난 일정)").

---

## 공통: 변경 이력 (모든 .md 수정 후 — hermes 스킬과 동일)

`TZ=Asia/Seoul date +"%Y-%m-%d %H:%M"`로 `{DATE} {TIME}`를 구해 **두 곳**에 기록한다.
기존 항목은 절대 수정/삭제하지 않으며 최신 항목이 항상 맨 위.

1. **수정한 파일의 `## History`** (파일 하단):
   - `## History` 헤딩 바로 아래(기존 항목 위)에 `- {DATE} {TIME} {action}` 삽입.
   - `## History`가 없으면 파일 맨 끝에 빈 줄 2개 + `---` + `## History` 헤딩과 함께 새로 만든다.
2. **통합 로그** `{vault}/wiki/log.md`:
   - `# Change Log` 헤딩 바로 아래에 다음 한 줄 삽입:
     `- {DATE} {TIME} \`Retrospective/1. Daily/{DATE}.md\` — {action}`
   - log.md가 없으면 `# Change Log` 헤딩으로 새로 만든다.

## 중요 규칙

- **대괄호 `[ ]` 절대 금지** — 모든 내용 평문. 위키링크/마크다운 링크 문법 금지. 순수 텍스트 + bullet(`*`)만.
- **파일이 이미 있으면 덮어쓰지 않는다** — 아침 A-2.
- **bullet만 교체** — 헤딩/구조/사람이 쓴 다른 섹션은 건드리지 않는다.
- **시각은 `TZ=Asia/Seoul date`로 확인** — 추측 금지.
- **데이터 소스 실패 시 중단하지 말고** 해당 섹션을 "…없음"으로 채우고 나머지를 진행한다.
- **History 기존 항목 보존** — 추가만, 수정/삭제 금지.

## Pitfalls

- **`google_api.py`는 Python 3.10+ 전용** — 파일 상단 `str | None` 타입힌트 때문에 **시스템 `python3`(3.9)로 부르면 import 단계에서 죽는다**(`TypeError: unsupported operand type(s) for |`). 죽으면 헬퍼 스크립트가 빈 결과를 받아 **거짓으로 "…없음"을 출력**한다(일정/메일이 있는데도 없다고 나오는 주범). → 헬퍼 스크립트는 `gws`/`google_api.py`를 `subprocess`로 부를 때 **`sys.executable`**(자기를 실행한 python)을 쓴다. 바닐라 `"python3"` 금지. cron은 venv python(3.11)으로 스크립트를 부르므로 `sys.executable`이면 안전. 직접 터미널 검증 시에도 `~/.hermes/hermes-agent/venv/bin/python`으로 부를 것.\n- **prenine 캘린더는 primary가 아니라 보조 캘린더에 일정이 산다** — 계정에 캘린더가 8개(개인=primary, 약속·회사·운동·생일 + 휴일·KBO·수원삼성 구독)인데 **실제 약속은 `약속`/`회사`/`운동`/`생일` 등 secondary 캘린더에 있다**. `calendarId=primary`만 조회하면 `[]`가 나와 거짓 "오늘 일정 없음"이 된다. → `calendar_today.py`는 `calendarList().list()`로 캘린더 목록을 받아 **포함 대상 캘린더들을 합쳐** 조회해야 한다(휴일·스포츠 구독은 보통 제외). 어떤 캘린더를 포함할지는 사용자 확정 목록을 따른다.\n- **\"…없음\" 결과는 의심하라** — 캘린더/메일이 빈 결과면 진짜 빈 건지, 위 두 버그(잘못된 python / primary-only)로 죽거나 누락된 건지 venv python으로 넓은 날짜·전체 캘린더로 교차 확인한다.\n- **Todoist 도구는 새 세션에서만 보인다** — cron은 항상 새 세션이라 OK. 대화형으로 테스트하려면 `/new` 후 확인.
- **완료 항목은 `todoist_completed_tasks_get` 말고 `todoist_activity_by_date_range`** — recurring 완료 누락 방지.
- **Google 계정 혼동 금지** — 캘린더=prenine, 메일=amoseui+prenine 합침. 스크립트가 알아서 처리하니 직접 토큰 경로를 만지지 말 것.
- **atom 피드의 커밋 메시지**는 `<content>` HTML의 `<blockquote>`에 있다(events API payload는 비어 옴). 스크립트가 처리하므로 직접 gh를 호출할 필요 없다.
- **vault root는 `amoseui` 두 번**(`.../Obsidian/amoseui/amoseui`). 한 단계 위로 쓰지 말 것.
- **공백 포함 경로**(`1. Daily`) 따옴표 처리 주의.

## 의존성
- `read_file` / `write_file` / `patch` / `terminal` (vault 파일 조작)
- `scripts/calendar_today.py` · `starred_mail.py` · `git_commits_today.py` (검증됨)
- google-workspace 스킬의 `google_api.py` + 계정별 `~/.hermes/google-accounts/{amoseui,prenine}/` 토큰
- Todoist MCP(`mcp-todoist`) — `todoist_task_get`, `todoist_activity_by_date_range`
- 인터넷(GitHub atom 피드)
