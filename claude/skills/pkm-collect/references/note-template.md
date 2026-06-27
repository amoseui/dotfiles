# work-note 구조 레퍼런스 (pkm-collect 노트 작성용)

이 노트는 `5. Claude/notes/`(Claude 전용 폴더)에만 생성한다. 사람이 쓴 노트와 섞지 않는다.

frontmatter:
---
created: {YYYY-MM-DD HH:MM:SS}
modified: {YYYY-MM-DD HH:MM:SS}
date: {YYYY-MM-DD}
tags:
  - {work|personal}      # base 정확히 1개
  - {주제태그}            # feature/fix/refactor/troubleshooting/dev … 중 적절히
---

본문 (파일명과 같은 H1 금지):

>[!summary]
>- 핵심 1
>- 핵심 2

# 목적
작업 배경/목적.

# 작업 내용
## 상세
구체 작업.
## 기술적 고려사항
- …

# 결과
결과 요약.

# 참고
- 세션: {claude/codex} {session_id 앞 8자}
- 브랜치: {branch}
- 설계/계획: {docs/superpowers/specs/...md, docs/superpowers/plans/...md}   # 참고한 superpowers 문서가 있을 때만
- {관련 PR/링크/[[관련 노트]]}


---
## History
- {YYYY-MM-DD HH:MM} 최초 생성 (pkm-collect 자동)
