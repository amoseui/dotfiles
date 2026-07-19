---
name: pkm-collect
description: |
  [수동 폴백] 이 맥북에서 Claude Code 대화 기록을 직접 분석해 PKM vault의
  "5. Claude/notes"에 노트로 합성하고 daily note에 백링크를 건다.
  ★ 평시 경로가 아니다: 평소에는 pkm-push가 digest를 인박스로 밀고 맥미니
  Hermes의 pkm-collect가 노트를 합성한다(단일 경로). 이 스킬은 Hermes가
  장애·부재 중일 때, 또는 사용자가 "맥북에서 직접" 정리를 원할 때만 쓴다.
  트리거 - "pkm collect 직접", "맥북에서 오늘 한 일 정리", "Hermes 없이 노트
  합성", "수동 collect" 등 이 머신에서 직접 합성하라는 명시적 요청 시.
---

# pkm-collect — 대화 기록 → PKM 노트 합성 (수동 폴백)

> **역할**: 평시 노트 합성은 `pkm-push`(이 맥북) → vault 인박스 →
> **맥미니 Hermes의 pkm-collect**가 담당하는 단일 경로다. 이 스킬은 그
> 경로가 막혔을 때(Hermes 장애·부재)나 사용자가 명시적으로 이 머신에서
> 직접 합성을 원할 때만 실행한다. 실행 전에 이 사실을 사용자에게 상기시킨다.

오늘 Claude Code 대화 기록 → PKM 노트 + daily note 백링크. **결정론 수집은
collect.py, 의미 판단·작성은 LLM**.

## 전제
- vault: `/Users/amoseui/Obsidian/amoseui` (config.yaml의 vault_path). cwd와 무관하게 이 vault에 작성한다.
- ★ **Claude가 자동 생성하는 노트는 사람 노트와 분리한다**: 노트 본체는 항상 **`5. Claude/notes/`** 안에만 만든다. 다른 PARA 폴더(`0. Inbox`, `1. Projects`, `3. Resources` 등)에 쓰지 않는다.
- 작성 전 반드시 **선정안 미리보기 + 사용자 승인**(4단계)을 거친다.
- vault `.md`를 만들거나 고칠 때는 `[[obsidian-history]]` 규칙을 따른다(아래 5단계 참고).

## 절차

### 0. config 로드
`~/.claude/skills/pkm-collect/config.yaml`을 Read. vault_path·note_dir·exclude·thresholds·time_buckets·journal_logs_heading 확인.

### 1. 수집 (collect.py 실행)
mktemp로 임시 파일을 만들고(zsh noclobber → `>|`) digest를 받는다:
```bash
DIGEST=$(mktemp /tmp/pkm_collect.XXXXXX)
python3 ~/.claude/skills/pkm-collect/scripts/collect.py \
  --vault "/Users/amoseui/Obsidian/amoseui" \
  --note-dir "5. Claude/notes" \
  --exclude-keywords "의료,병원,보험,건강검진,진료,대장내시경" >| "$DIGEST"
echo "$DIGEST"
```
- `--since`를 주지 않으면 state.json 마커(없으면 오늘 00:00)부터 수집한다.
- digest의 `generated_at`을 기억해 둔다(6단계 마커 갱신에 사용).
- digest를 Read. **원본 트랜스크립트는 절대 직접 읽지 않는다**(토큰 폭발 방지).

### 2~3. 작업항목 그룹핑 + 기록가치 평가 + 중복 판정
digest.sessions를 읽고:
- **그룹핑**: 같은 project + 같은/연속 branch + 같은 주제의 세션을 하나의 "작업 항목"으로 묶는다.
- **기록가치**: `triviality=="substantial"` 또는 의미 있는 의사결정/구현/트러블슈팅이면 CREATE 후보. 단순 Q&A·탐색만·중단된 시도는 제외.
- **중복(PR)**: `already_documented==true`(pr_url이 기존 노트에 있음)이거나 `skills_used`에 make-pr가 있으면 → `SKIP(PR중복)`.
- **중복(주제)**: `existing_notes_index`(오늘자 노트 제목)와 작업항목 주제가 겹치면 `SKIP(중복)`.

### 4. 선정안 미리보기 + 승인 (필수 게이트)
표로 제시: | 작업항목 | 프로젝트 | 시각 | 액션(CREATE/SKIP사유) | 제안 노트 제목 |
사용자가 항목 추가·제외·제목 수정·승인. **승인 전 어떤 파일도 쓰지 않는다.**

### 5. 노트 작성 + daily note 백링크
승인된 CREATE 항목마다:
1. 세부가 필요하면 해당 세션 `transcript_path`를 **타깃 grep/jq로만** 부분 조회(전체 읽기 금지).
   - **superpowers 작업 문서 참고**: 작업항목의 `project` repo 루트에 `docs/superpowers/specs/*.md`(brainstorming 설계)·`docs/superpowers/plans/*.md`(writing-plans 구현 계획)가 있으면, 이 작업과 **관련된 것만** 읽어 노트의 `# 목적`·`# 기술적 고려사항`(왜 했나·핵심 의사결정)을 보강한다. gitignore된 로컬 산출물이라 없을 수 있으니, 있을 때만 graceful하게 쓰고 없으면 조용히 건너뛴다. 참고한 문서는 노트 `# 참고`에 repo-상대경로로 출처를 남긴다.
     ```bash
     ls "$PROJECT"/docs/superpowers/specs/*.md "$PROJECT"/docs/superpowers/plans/*.md 2>/dev/null
     ```
2. `references/note-template.md` 구조로 **`/Users/amoseui/Obsidian/amoseui/5. Claude/notes/<한글 자연어 제목>.md`**를 **Write 도구로** 생성.
   - 폴더가 없으면 만든다(`5. Claude/notes/`).
   - frontmatter: created/modified(`date "+%Y-%m-%d %H:%M:%S"`)/date/tags.
   - tags: base(work|personal) 1개 + 주제태그. 업무 repo→work, 개인 dev→personal.
   - 파일명 한글, 영문 케밥케이스 금지. 동명 파일 있으면 제목 보강.
   - 템플릿대로 노트 맨 끝에 `## History`(최초 생성) 한 줄을 남긴다.
3. 오늘 daily note `/Users/amoseui/Obsidian/amoseui/Retrospective/1. Daily/$(date +%Y-%m-%d).md`에 백링크 추가:
   - 작업항목 대표 시각(started_at 로컬 시:분)으로 버킷 결정: <12:00 Morning / <18:00 Afternoon / 그 외 Evening.
   - config의 `journal_logs_heading`(기본 `## 🤖 Claude 작업 로그`) 섹션의 해당 `### Morning/Afternoon/Evening` 아래에 `- [[노트 제목]]` 추가(Edit 도구).
   - 이미 같은 링크가 있으면 추가하지 않는다(멱등). 해당 시간대 헤딩이 없으면 만든다. AI 전용 섹션이 없으면 daily note 맨 끝에 `## 🤖 Claude 작업 로그`를 새로 만들고 그 아래에 추가한다(사람이 쓴 다른 섹션은 건드리지 않는다).
   - daily note 파일 자체가 없으면 `Templates/template-retrospective-1-daily.md`를 참고해 stub을 만든 뒤 추가한다.
4. **obsidian-history 적용**: daily note(사람 파일)를 편집했으므로 `[[obsidian-history]]` 규칙에 따라 daily note의 `## History`와 `wiki/log.md`에 변경을 기록한다. `5. Claude/notes/`의 생성 노트는 AI 전용 영역이므로 노트 내 `## History`(최초 생성)만 남기고 `wiki/log.md`에는 중복 기록하지 않는다.

### 6. 마커 갱신
1단계에서 기억한 generated_at으로 마커를 저장:
```bash
python3 ~/.claude/skills/pkm-collect/scripts/collect.py \
  --vault "/Users/amoseui/Obsidian/amoseui" --update-marker "<generated_at>"
rm -f "$DIGEST"
```
완료 보고: 생성한 노트 목록과 daily note 백링크 위치, SKIP한 항목/사유 요약.

## 주의
- 민감(의료/개인) 세션은 collect.py가 digest에서 이미 제외 → LLM에 노출되지 않는다.
- 절대 원본 트랜스크립트 전체를 컨텍스트로 읽지 않는다. digest와 타깃 grep만 사용.
- Claude 생성 노트는 반드시 `5. Claude/` 아래에만 둔다(사람 노트 영역 오염 금지).
