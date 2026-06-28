---
name: pkm-collect
description: |
  하루 작업 종료 시(또는 밤 cron) 오늘의 Claude Code + Codex 사용 내역을 분석해
  기록 가치가 있는 작업만 골라 Obsidian vault의 hermes/notes 에 노트로 합성하고,
  오늘 daily note의 Hermes 작업 로그 섹션에 백링크를 건다. 이 메인 맥의 로컬 내역
  (~/.claude, ~/.codex)과, 보조 맥북이 pkm-push로 동기 vault 인박스에 밀어넣은 digest를
  함께 읽는다. 결정론 수집은 collect.py, 의미 판단·노트 작성은 LLM이 한다.
  트리거: "pkm collect", "오늘 한 일 정리", "작업 내역 정리", "하루 작업 노트",
  "codex claude 내역 정리", "일과 정리", daily collect, 밤 회고 시 작업 내역 수집 요청.
version: 1.0.0
author: Hermes Agent + Amos
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [pkm, obsidian, claude-code, codex, collect, journal, automation]
    category: note-taking
    related_skills: [hermes, pkm-push, daily-notes-automation]
---

# pkm-collect — Claude/Codex 사용 내역 → PKM 노트 + daily 백링크

오늘 Claude Code + Codex 대화 기록을 분석해 **기록 가치 있는 작업만** 노트로 만들고
오늘 daily note에 백링크를 건다. **결정론 수집은 collect.py, 의미 판단·작성은 LLM**.

> 이 스킬은 `hermes` PKM 스킬의 노트 구조·변경 이력 규칙을 따른다. vault 경로/규칙이
> 헷갈리면 `hermes` 스킬과 그 `config.yaml`을 기준으로 삼는다.

## 0. 고정 환경 (검증 완료)

| 항목 | 값 |
|------|----|
| Vault 루트 | `$CFG_vault_path` (config; 이 vault는 `amoseui` 두 번 중첩 구조) |
| AI 노트 폴더 | `{vault}/hermes/notes/` (사람 노트와 분리) |
| daily note | `{vault}/Retrospective/1. Daily/YYYY-MM-DD.md` |
| 백링크 섹션 | `## 🤖 Hermes 작업 로그` 의 `### Morning/Afternoon/Evening` |
| 통합 로그 | `{vault}/wiki/log.md` (헤딩 `# Change Log`) |
| 인박스(맥북) | `{vault}/hermes/inbox/codex-claude/*.json` (pkm-push 산출물) |
| 스킬 스크립트 | `~/.hermes/skills/note-taking/pkm-collect/scripts/` |
| 타임존 | Asia/Seoul (KST) |

데이터 소스:
- 이 맥 로컬: Claude `~/.claude/projects`, Codex `~/.codex/sessions`+`~/.codex/history.jsonl`
- 보조 맥북: `{vault}/hermes/inbox/codex-claude/*.json` (collect.py `--inbox-dir`로 합침)

## 절차

### 1. 수집 (collect.py 실행)
임시 파일에 digest를 받는다(zsh noclobber → `>|`). 인박스도 함께 합친다:
```bash
eval "$(python3 ~/.hermes/skills/note-taking/daily-notes-automation/scripts/_config.py --shell)"
VAULT="$CFG_vault_path"
DIGEST=$(mktemp /tmp/pkm_collect.XXXXXX)
python3 ~/.hermes/skills/note-taking/pkm-collect/scripts/collect.py \
  --vault "$VAULT" \
  --note-dir "hermes/notes" \
  --inbox-dir "$VAULT/hermes/inbox/codex-claude" \
  --exclude-keywords "의료,병원,보험,건강검진,진료,대장내시경" >| "$DIGEST"
echo "$DIGEST"
```
- `--since`를 주지 않으면 `state.json` 마커(없으면 오늘 00:00)부터 수집한다.
- digest의 `generated_at`을 기억(6단계 마커 갱신에 사용).
- digest를 `read_file`로 읽는다. **원본 트랜스크립트는 직접 읽지 않는다**(토큰 폭발 방지).
  세션의 `source`(claude/codex), `project`, `user_prompts`, `edited_files`, `inbox_origin` 등 메타만 본다.

### 2~3. 그룹핑 + 기록가치 평가 + 중복 판정
digest.sessions를 읽고:
- **그룹핑**: 같은 project + 같은/연속 branch + 같은 주제의 세션을 하나의 "작업 항목"으로 묶는다.
  로컬과 맥북(inbox_origin) 세션이 같은 project면 한 항목으로 합칠 수 있다(머신은 `# 참고`에 표기).
- **기록가치**: `triviality=="substantial"`(편집/커밋/PR 있음) 또는 의미 있는 의사결정/구현/트러블슈팅이면
  CREATE 후보. 단순 Q&A·탐색만·중단된 시도는 제외(collect.py가 trivial은 이미 드롭).
- **중복(PR)**: `already_documented==true` 또는 `skills_used`에 make-pr 있으면 → `SKIP(PR중복)`.
- **중복(주제)**: `existing_notes_index`(오늘자 노트 제목)와 주제가 겹치면 `SKIP(중복)`.

### 4. 선정안 미리보기 + 승인 (대화형일 때 필수 게이트)
표로 제시: | 작업항목 | 소스(claude/codex/머신) | 프로젝트 | 시각 | 액션(CREATE/SKIP사유) | 제안 노트 제목 |
사용자가 항목 추가·제외·제목 수정·승인. **승인 전 어떤 파일도 쓰지 않는다.**
> cron(비대화) 실행 시: 명백한 CREATE 후보만 자동 생성하고, 애매한 항목은 SKIP으로 보고만 한다.

### 5. 노트 작성 + daily note 백링크
승인된 CREATE 항목마다:
1. 세부가 필요하면 해당 세션 `transcript_path`를 **타깃 search_files/grep로만** 부분 조회(전체 읽기 금지).
   맥북(inbox) 세션은 transcript_path가 없을 수 있다 → digest 메타(prompts/edited_files)만으로 작성.
   - superpowers 참고: 작업 repo 루트에 `docs/superpowers/specs|plans/*.md`가 있으면 관련된 것만 읽어
     `# 목적`·`## 기술적 고려사항`을 보강하고 `# 참고`에 repo-상대경로 출처를 남긴다(없으면 조용히 건너뜀).
2. `references/note-template.md` 구조로 **`{vault}/hermes/notes/<한글 자연어 제목>.md`**를 `write_file`로 생성.
   - 폴더 없으면 자동 생성. 파일명과 같은 H1 금지. 파일명 한글, 영문 케밥케이스 금지. 동명 파일 있으면 제목 보강.
   - frontmatter: created/modified(`TZ=Asia/Seoul date +"%Y-%m-%d %H:%M:%S"`)/date/tags.
   - tags: base(work|personal) 1개 + 주제태그. 업무 repo→work, 개인 dev→personal.
   - `# 참고`에 세션 출처: `세션: {claude|codex} {session_id 앞 8자}` + 머신(로컬/맥북) + 브랜치.
   - 노트 맨 끝 `## History` 첫 줄: `- {DATE} {TIME} 최초 생성 (pkm-collect)`.
3. 오늘 daily note `{vault}/Retrospective/1. Daily/{DATE}.md`에 백링크 추가:
   - 작업항목 대표 시각(started_at 로컬 시:분)으로 버킷: <12:00 Morning / <18:00 Afternoon / 그 외 Evening.
   - `## 🤖 Hermes 작업 로그` 섹션의 해당 `### Morning/Afternoon/Evening` 아래에 `- [[노트 제목]]` 추가(`patch`).
   - 이미 같은 링크 있으면 스킵(멱등). 시간대 헤딩 없으면 만든다. AI 섹션 자체가 없으면 daily note 맨 끝에
     `## 🤖 Hermes 작업 로그`를 새로 만들고 그 아래 추가(사람이 쓴 다른 섹션은 건드리지 않는다).
   - daily note 파일이 없으면 `Templates/template-retrospective-1-daily.md` 참고로 stub 생성 후 추가.
4. **변경 이력**: daily note(사람 파일) 편집했으므로 `hermes` 스킬 "변경 이력 규칙"에 따라 daily note의
   `## History` + `wiki/log.md`에 기록. `hermes/notes/`의 생성 노트는 AI 전용이므로 노트 내 `## History`
   (최초 생성)만 남기고 `wiki/log.md`에는 중복 기록하지 않는다.

### 6. 마커 갱신 + 인박스 정리
1단계에서 기억한 generated_at으로 마커를 저장하고, 처리한 인박스 파일을 보관 폴더로 옮긴다:
```bash
python3 ~/.hermes/skills/note-taking/pkm-collect/scripts/collect.py \
  --vault "$VAULT" --update-marker "<generated_at>"
# 처리 완료한 맥북 digest는 재처리 방지를 위해 보관 폴더로 이동(삭제 아님)
DONE="$VAULT/hermes/inbox/codex-claude/_processed"
mkdir -p "$DONE"
# 이번에 실제로 반영한 inbox_origin 파일만 이동(없으면 생략)
# 예: mv "$VAULT/hermes/inbox/codex-claude/macbook-2026-06-28-2200.json" "$DONE/"
rm -f "$DIGEST"
```
완료 보고: 생성한 노트 목록 + daily note 백링크 위치, SKIP한 항목/사유, 처리한 인박스 파일.

## 주의 / Pitfalls
- **원본 트랜스크립트 전체를 컨텍스트로 읽지 않는다** — digest와 타깃 grep만 사용.
- 민감(의료/개인) 세션은 collect.py가 digest에서 이미 제외 → LLM에 노출 안 됨.
- **AI 생성 노트는 `hermes/notes/` 밖으로 안 나간다**(사람 노트 영역 오염 금지).
- **인박스 재처리 방지**: 처리한 맥북 digest는 `_processed/`로 옮기거나, 마커(state.json) since로 거른다.
  단 마커는 이 맥 로컬 mtime 기준이라, 인박스는 started_at 기준으로 합쳐지므로 `_processed/` 이동이 가장 확실.
- **Codex 세션은 transcript_path가 없을 수 있다**(맥북 inbox) — digest 메타만으로 노트 작성.
- **vault root는 config `vault_path` 기준** — 이 vault는 `amoseui` 두 번 중첩 구조다. dotfiles의 Claude Code용 pkm-collect는 한 단계 위 경로 + `5. Claude/notes`를 쓰지만, Hermes판은 config의 `vault_path` + `hermes/notes`다(혼동 금지).
- 시각은 `TZ=Asia/Seoul date`로 확인(추측 금지).

## 의존성
- `read_file` / `write_file` / `patch` / `search_files` / `terminal`
- `scripts/collect.py` + `claude_digest.py` · `codex_digest.py` · `notes_index.py` (stdlib only)
- `references/note-template.md`
- 동기 vault 인박스(맥북 pkm-push 산출물) — 없으면 로컬 내역만 처리
- `hermes` 스킬(노트 구조·변경 이력 규칙)
