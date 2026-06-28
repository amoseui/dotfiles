# 노트 구조 레퍼런스 (hermes 스킬용)

> 이 템플릿의 노트는 config.yaml의 `note_dir`(기본 `hermes/notes/`) 또는
> `media_dir`(책/영화, 기본 `hermes/media/`)에만 생성한다.
> 사람이 쓴 노트나 다른 에이전트 폴더(`5. Claude/` 등)와 섞지 않는다.
> 파일명과 같은 H1 은 쓰지 않는다(파일명이 제목 역할).
> created/modified/date/History 시각은 추측하지 말고 `date` 명령으로 확인해 넣는다.

---

## A. 일반 / work 노트  (note_dir)

```markdown
---
created: {YYYY-MM-DD HH:MM:SS}
modified: {YYYY-MM-DD HH:MM:SS}
date: {YYYY-MM-DD}
tags:
  - {work|personal}      # base 정확히 1개 (업무 repo→work, 개인→personal)
  - {주제태그}            # feature/fix/refactor/docs/chore/troubleshooting/planning/dev …
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
- 세션: hermes {session_id 앞 8자}   # 알 수 있을 때만
- 브랜치: {branch}                    # repo 작업일 때만
- {관련 PR/링크/[[관련 노트]]}


---
## History
- {YYYY-MM-DD HH:MM} 최초 생성 (hermes)
```

단순 메모는 `# 작업 내용`/`# 결과`/`# 참고`를 상황에 맞게 생략 가능.
work 노트(개발·작업 기록)는 위 전체 구조를 따른다.

---

## B. PR 문서화 노트  (note_dir)

```markdown
---
created: {YYYY-MM-DD HH:MM:SS}
modified: {YYYY-MM-DD HH:MM:SS}
date: {YYYY-MM-DD}
tags:
  - work
  - {PR 타입 주제 태그}   # feat→feature, fix→fix, refactor→refactor, docs→docs, chore/ci/test→chore …
pr_url: {URL}
repository: {repo-name}   # gh pr view --json headRepository --jq '.headRepository.name'
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
- **설계/계획**: {docs/superpowers/specs/...md, plans/...md}   # 있을 때만


---
## History
- {YYYY-MM-DD HH:MM} 최초 생성 (hermes, PR 문서화)
```

파일명: `{repo} - PR{번호} - {설명}`. `#` 금지, `feat:`/`fix:` prefix 제거(태그로 표현),
특수문자(`/\:*?"<>|#`)→`-`.

---

## C. 영화 노트  (media_dir)

```markdown
---
created: {YYYY-MM-DD HH:MM:SS}
modified: {YYYY-MM-DD HH:MM:SS}
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

## 내용 요약

## 느낀 점


---
## History
- {YYYY-MM-DD HH:MM} 최초 생성 (hermes)
```

TMDB 키(`$TMDB_API_KEY`)가 있으면 메타데이터 자동완성, 없으면 빈 채로 생성(하드코딩 금지).

---

## D. 책 노트  (media_dir)

```markdown
---
created: {YYYY-MM-DD HH:MM:SS}
modified: {YYYY-MM-DD HH:MM:SS}
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

## 내용 요약

## 느낀 점


---
## History
- {YYYY-MM-DD HH:MM} 최초 생성 (hermes)
```
