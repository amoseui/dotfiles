---
name: pkm
description: |
  Obsidian PKM vault 관리 스킬. 노트 생성/편집/검색, Daily Journal 백링크, PR 문서화, 책/영화 노트(TMDB) 생성 지원.
  트리거: "pkm" 키워드, "노트 작성/추가/편집" 요청, "저널에 기록" 요청,
  PR URL/번호 언급 + 문서화 요청, "vault에서 찾아줘" 검색,
  "책 추가", "영화 추가", "book", "movie", "읽은 책", "본 영화" 등 도서/영화 노트 생성 요청 시.
---

# PKM Skill - Obsidian Vault 관리

사용자가 요청하는 vault 작업(노트 작성/편집/검색, 저널, PR 문서화, 책/영화)을 수행한다.

## Vault 경로

> [!CRITICAL] **절대 경로 — 반드시 준수**
> - **Vault root**: `/Users/amoseui/Obsidian/amoseui`
> - 모든 파일 작업은 이 경로 하위에서만 수행한다.

### ★ Claude 생성 문서 분리 (사용자 규칙)

Claude가 만드는 모든 노트는 사람이 쓴 노트와 섞지 않고 **전용 폴더 `5. Claude/`** 아래에만 둔다.

| 종류 | 위치 |
|------|------|
| 일반 노트 / PR 문서 | `5. Claude/notes/` |
| 책/영화 노트 | `5. Claude/media/` |
| Daily Journal 백링크 | `Retrospective/1. Daily/YYYY-MM-DD.md`의 `## 🤖 Claude 작업 로그` 섹션 (백링크만, 노트 본체는 위 폴더에) |

다른 PARA 폴더(`0. Inbox`, `1. Projects`, `2. Areas`, `3. Resources` 등)에 직접 쓰지 않는다.

## 도구 사용 규칙 (obsidian-cli 미사용)

이 머신엔 `obsidian` CLI가 없다. vault 파일은 **Read / Edit / Write 도구로 직접** 조회·작성·편집한다.

- 새 노트: `Write`로 절대 경로에 생성. 폴더가 없으면 만든다.
- 기존 노트 편집: 먼저 `Read`로 읽고 `Edit`로 정확한 위치만 수정(기존 내용 보존, 중복 방지).
- 검색: `Grep`(내용) / `Glob`(파일명)으로 vault 하위 탐색. 공백 포함 경로 주의.
- **vault `.md`를 만들거나 고칠 때는 반드시 `[[obsidian-history]]` 규칙을 따른다**(노트 하단 `## History` + `wiki/log.md` 기록).

## 공통 규칙: frontmatter 시간

`created`/`modified`에는 `Bash`로 실제 시간을 확인해 넣는다(추측 금지):

```bash
date '+%Y-%m-%d %H:%M:%S'
```
- 생성 시: `created` = `modified` = 현재 시간
- 편집 시: `modified`만 현재 시간으로 갱신

frontmatter·태그 규칙(최소):
- base 태그 정확히 1개: `work` | `personal` (업무 repo→work, 개인→personal)
- 주제 태그: feature/fix/refactor/docs/chore/troubleshooting/planning/dev/book/movie 등에서 적절히
- 파일명: 한글 자연어, 특수문자(`/\:*?"<>|#`)→`-`, 최대 100자

---

## 1. 노트 생성

위치: `5. Claude/notes/<제목>.md`. `Write`로 생성:

```markdown
---
created: {NOW}
modified: {NOW}
date: {YYYY-MM-DD}
tags:
  - {work|personal}
  - {주제태그}
---

>[!summary]
>- 핵심 1

# 목적
...

# 내용
...


---
## History
- {YYYY-MM-DD HH:MM} 최초 생성 (pkm)
```

생성 후 `[[obsidian-history]]`에 따라 `wiki/log.md`에도 한 줄 기록한다.

## 2. 노트 편집

1. `Read`로 기존 내용 확인
2. `Edit`로 해당 부분만 수정(기존 보존, 중복 방지)
3. frontmatter `modified` 갱신
4. `## History`에 항목 추가 + `wiki/log.md` 기록 (`[[obsidian-history]]`)

## 3. 노트 검색

- 내용 검색: `Grep`로 vault 하위에서 검색어 탐색(`path` 지정 가능)
- 파일명/폴더: `Glob`(예: `5. Claude/notes/*.md`)
- 결과를 사용자에게 목록으로 제시

---

## 4. Daily Journal 백링크

### 위치
`/Users/amoseui/Obsidian/amoseui/Retrospective/1. Daily/YYYY-MM-DD.md`

### 시간대 판단
- 00:00~05:59 (새벽) → **전날** 날짜의 Evening (아직 안 잔 것으로 간주)
- 06:00~11:59 → 당일 Morning / 12:00~17:59 → Afternoon / 18:00~23:59 → Evening

### 절차
1. 대상 daily note를 `Read`로 읽는다.
2. `## 🤖 Claude 작업 로그` 섹션의 해당 `### Morning/Afternoon/Evening` 아래에 `- [[노트 제목]]`을 `Edit`로 삽입한다.
   - 이미 같은 백링크가 있으면 스킵(멱등). 시간대 헤딩이 없으면 만든다.
   - `## 🤖 Claude 작업 로그` 섹션 자체가 없으면 daily note **맨 끝**에 새로 만들고 그 아래 추가한다(사람이 쓴 다른 섹션은 건드리지 않는다).
3. daily note 파일이 없으면 `Templates/template-retrospective-1-daily.md`를 참고해 stub을 만든 뒤 추가한다.
4. daily note는 사람 파일이므로 편집 후 `[[obsidian-history]]` 규칙(`## History` + `wiki/log.md`)을 적용한다.

---

## 5. PR 문서화

GitHub PR을 work 노트로 변환해 **`5. Claude/notes/`**에 기록한다.

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


---
## History
- {YYYY-MM-DD HH:MM} 최초 생성 (pkm, PR 문서화)
```

PR 타입 → 주제 태그: feat/feature→feature, fix→fix, refactor→refactor, docs→docs, chore/build/ci/test→chore, "troubleshoot/debug"→troubleshooting, "plan/design"→planning, 판단 불가→feature.

생성 후 `wiki/log.md`에 한 줄 기록(`[[obsidian-history]]`).

---

## 6. 책/영화 노트

위치: **`5. Claude/media/<제목>.md`**.

### 제목 확인
사용자 입력에서 제목 추출(예: "오펜하이머 영화 추가" → `오펜하이머`). 알 수 없으면 `AskUserQuestion`.

### 중복 확인
`Glob`/`Grep`으로 `5. Claude/media/`에 동일 제목 파일이 있으면 알리고 중단.

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

생성 후 `wiki/log.md`에 한 줄 기록(`[[obsidian-history]]`).

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
