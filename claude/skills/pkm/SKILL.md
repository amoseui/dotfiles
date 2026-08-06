---
name: pkm
description: |
  Obsidian PKM vault 관리 스킬. 노트 생성/편집/검색, Daily Journal 백링크, PR 문서화, 책/영화 노트(TMDB) 생성 지원.
  트리거: "pkm" 키워드, "노트 작성/추가/편집" 요청, "저널에 기록" 요청,
  PR URL/번호 언급 + 문서화 요청, "vault에서 찾아줘" 검색,
  "책 추가", "영화 추가", "book", "movie", "읽은 책", "본 영화" 등 도서/영화 노트 생성 요청 시.
---

# pkm — Obsidian vault 관리

사용자가 요청하는 vault 작업(노트 작성/편집/검색, 저널, PR 문서화, 책/영화)을 수행한다.

## 공통 규칙 단일 참조

플랫폼 공통 PKM 규칙은 `~/.claude/skills/note-taking-core.md`를 먼저 읽는다.
이 파일은 dotfiles의 `shared/note-taking/CORE.md`로 연결된 단일 참조다.
이 문서에는 Claude의 Read/Edit/Write/Grep 도구 매핑과 Claude 전용 작업만 둔다.
공통 규칙과 아래의 오래된 상세 설명이 충돌하면 단일 참조를 따른다.

## Vault 경로

> [!CRITICAL] **절대 경로 — 반드시 준수**
> - **Vault root**: `/Users/amoseui/Obsidian/amoseui`
> - 모든 파일 작업은 이 경로 하위에서만 수행한다.

### ★ Claude 생성 문서 분리 (사용자 규칙)

Claude가 만드는 모든 노트는 사람이 쓴 노트와 섞지 않고 **전용 영역 `6-agents/`** 아래(`6-agents/notes/`·`6-agents/media/`)에만 둔다.

| 종류 | 위치 |
|------|------|
| 일반 노트 / PR 문서 | `6-agents/notes/` |
| 책/영화 노트 | `6-agents/media/` |
| Daily Journal 백링크 | `2-journal/daily/YYYY-MM-DD.md`의 `## 🤖 Claude 작업 로그` 섹션 (백링크만, 노트 본체는 위 폴더에) |

사람 존 폴더(`1-inbox/`, `3-projects/`, `4-areas/`, `2-journal/`)에 직접 쓰지 않는다 (daily note의 지정 섹션 편집은 예외).

## 도구 사용 규칙 (obsidian-cli 미사용)

이 머신엔 `obsidian` CLI가 없다. vault 파일은 **Read / Edit / Write 도구로 직접** 조회·작성·편집한다.

- 새 노트: `Write`로 절대 경로에 생성. 폴더가 없으면 만든다.
- 기존 노트 편집: 먼저 `Read`로 읽고 `Edit`로 정확한 위치만 수정(기존 내용 보존, 중복 방지).
- 검색: `Grep`(내용) / `Glob`(파일명)으로 vault 하위 탐색. 공백 포함 경로 주의.
- **vault `.md`를 만들거나 고칠 때는 반드시 `[[obsidian-history]]` 규칙을 따른다**(노트 하단 `## History` + 감사 로그 `6-agents/state/changelog/YYYY-MM.md` 기록).

## Claude 어댑터 규칙

- 공통 frontmatter·시간·태그·superpowers·entity 참조 규칙은 `~/.claude/skills/note-taking-core.md`에서 읽는다.
- 이 문서에서만 Claude 전용 도구 매핑, `author: claude`, PR/미디어 절차를 정의한다.
- 공통 규칙과 legacy 상세 절차가 충돌하면 CORE가 우선한다.

## ★ 중복 방지 — 세션 기록은 Hermes 단일 경로

이 절은 **"오늘 무슨 작업을 했는지"를 남기는 세션 작업 기록 노트에만** 적용된다.
아래 표의 다른 노트들은 이 제한과 무관하며 평소대로 만든다.

| 노트 종류 | 이 제한 적용? |
|---|---|
| **세션 작업 기록** (오늘 한 작업을 사후 정리) | **적용** — 아래 규칙 따름 |
| PR 문서화 (§5) | 적용 안 함 — 요청 시 평소대로 생성 |
| 책·영화 노트 (§6) | 적용 안 함 |
| 사용자가 특정 주제를 지정한 조사·분석·기획 노트 | 적용 안 함 |
| 기존 노트 편집·보강, 검색, daily 백링크 | 적용 안 함 |

> [!IMPORTANT]
> **세션 작업 기록은 Claude가 먼저 나서서 노트로 만들지 않는다.** 평시 경로는 하나뿐이다:
> `pkm-push`(이 머신에서 digest 생성 → 공유 인박스) → **Hermes의 `pkm-collect`가 노트 합성**.
> 즉 사용자가 시키지 않았는데 "오늘 작업 정리해뒀습니다"를 하지 않는다는 뜻이다.

사용자가 **명시적으로** "지금 노트로 정리해줘"라고 요청하면 만든다. 단 그때도 **먼저 중복을 검색한다**:

- `Glob`으로 `6-agents/notes/*.md` 파일명 목록 확인 (제목 키워드 대조)
- 해당 날짜 daily note의 `## 🤖 Hermes/Claude/Grok 작업 로그` 섹션 확인

**같은 날짜(±1일)·같은 주제의 노트가 이미 있으면 새로 만들지 말고 그 노트를 보강한다**
(`## History`에 보강 항목 추가). 작성자가 hermes/grok이어도 마찬가지다 — 같은 작업을 두 번 기록하지 않는다.
검색 결과가 없으면 그냥 만들면 된다.

**배경**: 2026-07-30에 pkm-collect가 23:29·23:57 두 번 실행되어 같은 세션 5건(codegraph OOM,
T120 WebAuthn, orca zsh history, BattleStage, research-loop)이 claude/hermes 이름으로 이중 기록됐다.
2026-08-06에 claude판을 정본으로 통합하고 중복본 5건을 삭제했다.

### daily note 작업 로그 섹션

에이전트별로 섹션을 나눈다 — `## 🤖 Claude 작업 로그` / `## 🤖 Hermes 작업 로그` / `## 🤖 Grok 작업 로그`.
**자신이 실제로 작성한 노트만 자기 섹션에 백링크한다.** 다른 에이전트가 만든 노트를 보강했을 뿐이라면
해당 노트의 `## History`에만 남기고, 백링크를 자기 섹션에 중복 추가하지 않는다.
frontmatter의 `author`는 최초 작성자, `modified_by`는 보강한 에이전트를 뜻한다.

---

## 1. 노트 생성

위치: `6-agents/notes/<제목>.md`. `Write`로 생성. **파일명과 같은 H1은 쓰지 않는다**(파일명이 제목 역할):

```markdown
---
created: {NOW}
modified: {NOW}
date: {YYYY-MM-DD}
tags:
  - {work|personal}
  - {주제태그}
author: claude
---

>[!summary]
>- 핵심 1
>- 핵심 2

# 목적
작업 배경/목적.

# 작업 내용
## 상세
구체 작업 내용.
## 기술적 고려사항
- …

# 결과
결과 요약.

# 참고
- 세션: claude {session_id 앞 8자}   # 알 수 있을 때만
- 브랜치: {branch}                    # repo 작업일 때만
- {관련 PR/링크/[[관련 노트]]}


---
## History
- {YYYY-MM-DD HH:MM} 최초 생성 (pkm)
```

- 단순 메모 등 내용이 적으면 `# 작업 내용`/`# 결과`/`# 참고`는 상황에 맞게 생략 가능. work 노트(개발·작업 기록)는 위 전체 구조를 따른다.
- `# 참고`의 세션·브랜치는 출처 역추적용 — 알 수 있을 때만 채운다.
- work 노트는 **공통 규칙: superpowers 작업 문서 참고**를 적용한다 — repo에 spec/plan이 있으면 `# 목적`·`## 기술적 고려사항`을 보강하고 `# 참고`에 경로를 남긴다.

생성 후 `[[obsidian-history]]`에 따라 감사 로그(`6-agents/state/changelog/YYYY-MM.md`)에도 한 줄 기록한다.

## 2. 노트 편집

1. `Read`로 기존 내용 확인
2. `Edit`로 해당 부분만 수정(기존 보존, 중복 방지)
3. frontmatter `modified` 갱신
4. `## History`에 항목 추가 + 감사 로그(`6-agents/state/changelog/YYYY-MM.md`) 기록 (`[[obsidian-history]]`)

## 3. 노트 검색

- 내용 검색: `Grep`로 vault 하위에서 검색어 탐색(`path` 지정 가능)
- 파일명/폴더: `Glob`(예: `6-agents/notes/*.md`)
- 결과를 사용자에게 목록으로 제시

---

## 4. Daily Journal 백링크

### 위치
`/Users/amoseui/Obsidian/amoseui/2-journal/daily/YYYY-MM-DD.md`

### 시간대 판단
- 00:00~05:59 (새벽) → **전날** 날짜의 Evening (아직 안 잔 것으로 간주)
- 06:00~11:59 → 당일 Morning / 12:00~17:59 → Afternoon / 18:00~23:59 → Evening

### 절차
1. 대상 daily note를 `Read`로 읽는다.
2. `## 🤖 Claude 작업 로그` 섹션의 해당 `### Morning/Afternoon/Evening` 아래에 `- [[노트 제목]]`을 `Edit`로 삽입한다.
   - 이미 같은 백링크가 있으면 스킵(멱등). 시간대 헤딩이 없으면 만든다.
   - `## 🤖 Claude 작업 로그` 섹션 자체가 없으면 daily note **맨 끝**에 새로 만들고 그 아래 추가한다(사람이 쓴 다른 섹션은 건드리지 않는다).
3. daily note 파일이 없으면 `Templates/template-retrospective-1-daily.md`를 참고해 stub을 만든 뒤 추가한다.
4. daily note는 사람 파일이므로 편집 후 `[[obsidian-history]]` 규칙(`## History` + 감사 로그 `6-agents/state/changelog/YYYY-MM.md`)을 적용한다.

---

## 5. PR 문서화

GitHub PR을 work 노트로 변환해 **`6-agents/notes/`**에 기록한다. PR이 속한 repo에 superpowers spec/plan이 있으면 **공통 규칙: superpowers 작업 문서 참고**에 따라 `## 기술적 의사결정`을 보강하고 `## 참고`에 경로를 남긴다.

### PR 정보 수집
- **URL 제공 시**: `gh pr view {url} --json ...`
- **번호만 제공 시**: 현재 repo 기준 `gh pr view {번호}`. 모호하면 사용자에게 repo 확인.

### 파일명 규칙
- `{repo} - PR{번호} - {설명}` 형식. repo 이름은 `gh pr view --json headRepository --jq '.headRepository.name'`(kebab-case 그대로).
- frontmatter `repository:` 필드와 같은 값 사용. `#` 금지, `feat:`/`fix:` 등 type prefix 제거(태그로 표현).
- 특수문자(`/\:*?"<>|#`)→`-`.
- (선택) 이슈 트래커 티켓 번호를 알면 `{티켓번호} - {설명}` 형식도 가능.

### PR Work 노트 구조

```markdown
---
created: {NOW}
modified: {NOW}
date: {YYYY-MM-DD}
tags:
  - work
  - {PR 타입 주제 태그}
pr_url: {URL}
repository: {repo-name}
author: claude
---

>[!summary]
>- 핵심 변경 1~3개

## 개요
- **목적**: …
- **변경 범위**: …
- **상태**: OPEN/MERGED/CLOSED

## 변경사항
### 주요 구현
- **[파일/모듈]**: 변경 내용

## 기술적 의사결정
| 선택지 | 이유 | Trade-off |
|--------|------|-----------|

## 테스트
- 검증 결과: Pass/Fail

## 참고
- **PR**: {URL}
- **설계/계획**: {docs/superpowers/specs/...md, docs/superpowers/plans/...md}   # 참고한 superpowers 문서가 있을 때만


---
## History
- {YYYY-MM-DD HH:MM} 최초 생성 (pkm, PR 문서화)
```

PR 타입 → 주제 태그: feat/feature→feature, fix→fix, refactor→refactor, docs→docs, chore/build/ci/test→chore, "troubleshoot/debug"→troubleshooting, "plan/design"→planning, 판단 불가→feature.

생성 후 감사 로그(`6-agents/state/changelog/YYYY-MM.md`)에 한 줄 기록(`[[obsidian-history]]`).

---

## 6. 책/영화 노트

위치: **`6-agents/media/<제목>.md`**.

### 제목 확인
사용자 입력에서 제목 추출(예: "오펜하이머 영화 추가" → `오펜하이머`). 알 수 없으면 `AskUserQuestion`.

### 중복 확인
`Glob`/`Grep`으로 `6-agents/media/`에 동일 제목 파일이 있으면 알리고 중단.

### 영화 Frontmatter
```yaml
---
created: {NOW}
modified: {NOW}
tags:
  - personal
  - movie
watch_date:
status: TO WATCH
title: "제목"
genre: []
director: []
actor: []
release_year:
cover:
rating: ⭐️
comment:
---
```

본문: `## 내용 요약` / `## 느낀 점`.

### TMDB 자동완성 (선택)
`config.yaml`의 `tmdb.api_key` 또는 환경변수 `$TMDB_API_KEY`가 있으면 메타데이터를 자동으로 채운다. **키가 없으면 TMDB를 건너뛰고** cover 등을 빈 채로 노트를 만든다(하드코딩 금지).

```bash
curl -s "https://api.themoviedb.org/3/search/movie?api_key={KEY}&query={제목}&language=ko-KR"
# TV: .../search/tv?...
```
- 첫 결과 사용. `poster_path`→`cover: https://image.tmdb.org/t/p/w500/{poster_path}`, `release_date`→`release_year`(연도), `genre_ids`→`genre`(한글 변환).
- 한글 검색 실패 시 `original_title`로 재시도. 감독/출연: `/movie/{id}/credits`에서 `job:"Director"`→director, `cast` 상위 3~5→actor.

TMDB 장르 ID→한글: 28 액션, 12 모험, 16 애니메이션, 35 코미디, 80 범죄, 99 다큐멘터리, 18 드라마, 10751 가족, 14 판타지, 36 역사, 27 공포, 10402 음악, 9648 미스터리, 10749 로맨스, 878 SF, 53 스릴러, 10752 전쟁, 37 서부, 10770 TV 영화.

### 책 Frontmatter
```yaml
---
created: {NOW}
modified: {NOW}
tags:
  - personal
  - book
start:
finish:
status: TO READ
title: "제목"
genre:
author:
isbn:
cover:
rating: ⭐️
comment:
---
```
본문: `## 내용 요약` / `## 느낀 점`. 저자·장르 등 추가 정보 제공 시 기입. cover는 웹 검색으로 채울 수 있음(선택).

생성 후 감사 로그(`6-agents/state/changelog/YYYY-MM.md`)에 한 줄 기록(`[[obsidian-history]]`).

---

## 에러 처리
| 상황 | 처리 |
|------|------|
| 파일 미존재 | `Write`로 새로 생성 |
| 섹션 미존재 | 해당 섹션을 만들어 추가 |
| 중복 백링크 | `Read`로 확인 후 있으면 스킵 |
| PR 미발견 | 에러 메시지 출력 |
| TMDB 키 없음 | TMDB 건너뛰고 빈 메타로 생성 |

## 의존성
- `Read`/`Edit`/`Write`/`Grep`/`Glob` (vault 파일 직접 조작 — obsidian-cli 불필요)
- `[[obsidian-history]]` 스킬 (vault 변경 이력 기록)
- `gh` CLI (PR 문서화 시)
- (선택) `$TMDB_API_KEY` 또는 config.yaml `tmdb.api_key` (책/영화 메타데이터)
