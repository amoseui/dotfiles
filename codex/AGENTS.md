# Global Codex guidance

- 사용자에게 한국어로 응답하고, 기술 용어·코드 식별자는 원문을 유지한다.
- 코드 주석과 커밋 메시지는 영어로 작성한다. 커밋 형식·포맷·빌드·검증 명령은 해당 저장소의 규칙을 따른다.
- Chromium 커밋 제목은 `cl-description` 스킬에 맞춰 `[모듈] ...` 형식으로 작성한다(예: `[CSS] ...`, `[a11y] ...`). 모듈명의 대소문자는 해당 영역의 기존 관례를 따른다.
- Chromium 커밋 메시지에는 `Test:` footer를 작성하지 않는다. `cl-description` 등 스킬·템플릿에서 요구하더라도 이 사용자 규칙을 우선한다. 필요한 테스트와 검증은 수행하고, 결과는 작업 보고에 남긴다.
- Git 개발 브랜치를 새로 만들 때는 생성일(사용자 로컬 시간대)의 `YYMMDD-`를 이름 맨 앞에 붙인다(예: `260912-cssstylerule-inherits-grouping-rule`). 날짜는 브랜치 생성 시점에 확인한다.
- 사실과 추정을 구분하고, 완료·통과를 보고하기 전에 실제 결과와 산출물을 확인한다. 검증하지 못한 범위도 명시한다.
- 요청과 직접 관련된 범위만 수정하고, 기존 미커밋 변경을 보존한다.
- 이미 승인된 작업과 가역적인 수정은 계속 진행한다. 선택적인 스킬 절차 때문에 같은 허가를 반복해서 묻지 않는다.
- Chromium 개발에서는 저장소 규모 때문에 git worktree를 만들지 않는다.
- 스킬에 Claude의 `Read/Edit/Write/Bash/Grep/Glob`가 나오면 현재 제공된 읽기·패치·쉘·검색 도구로 대응한다. `Skill` 도구가 없으면 해당 `SKILL.md`를 직접 읽는다.
- Claude 플러그인의 `/codex:review`·`/codex:adversarial-review`는 Codex 명령이 아니다. Codex에서는 사용 가능한 review 기능이나 독립 검토자를 쓰고 실제 검토 범위를 보고한다.

<!-- CODEGRAPH_START -->
## CodeGraph

In repositories indexed by CodeGraph (a `.codegraph/` directory exists at the repo root), reach for it BEFORE grep/find or reading files when you need to understand or locate code:

- **MCP tool** (when available): `codegraph_explore` answers most code questions in one call — the relevant symbols' verbatim source plus the call paths between them, including dynamic-dispatch hops grep can't follow. Name a file or symbol in the query to read its current line-numbered source. If it's listed but deferred, load it by name via tool search.
- **Shell** (always works): `codegraph explore "<symbol names or question>"` prints the same output.

If there is no `.codegraph/` directory, skip CodeGraph entirely — indexing is the user's decision.
<!-- CODEGRAPH_END -->
