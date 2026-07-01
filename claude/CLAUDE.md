# Global Claude memory

모든 Claude Code 세션에 로드되는 개인 환경 설정과 작업 규약.

## 응답·사고 언어
- 모든 응답은 한국어로 한다. (하니스 차원에서도 강제됨)
- 사고(thinking) 과정도 한국어로 진행한다.
- 기술 용어·코드 식별자는 원문 그대로 둔다.

## 작업 진행 표시
도구를 호출하기 전에, 무엇을 하는지 한 줄로 이모지와 함께 알린다.

| 이모지 | 상황 |
|--------|------|
| 🔧 | 파일 읽기·편집·쓰기 (Read/Edit/Write) |
| 🔍 | 코드 검색 (Grep/Glob) |
| ⚡ | Bash 명령 실행 |
| 🌐 | 웹 조회 (WebFetch/WebSearch) |
| 🤖 | 서브에이전트(Agent) 기동 |
| 🧩 | 워크플로우·병렬 작업 |
| 🎯 | 스킬(Skill) 활성화 |
| 📋 | 태스크(Task) 생성·갱신 |
| 🔌 | MCP 도구 호출 |

예: `🔧 globals.css 읽는 중…`

## 코드 작성 규칙
- 코드 주석은 영어로 작성한다.
- 커밋 메시지는 영어로 작성한다 (type prefix 포함 — feat/fix/refactor/chore 등).
- 라인 길이·포맷은 전역 고정값을 두지 않고, 해당 프로젝트 설정(.clang-format / .prettierrc / .editorconfig 등)을 따른다.
- 기존 코드의 컨벤션(네이밍·구조·주석 밀도)을 우선 따른다.

## 팩트와 의견 분리
- 객관적 사실과 AI의 주관적 추정·제안을 구분한다.
- 주관적 분석·추천에는 `[AI의견]` 태그를 앞에 붙인다.
- 예: `[AI의견] 이 구조는 추후 캐싱 도입 시 유리해 보입니다.`

## 검증·엄밀성
- 완료·통과를 주장하기 전에 종료코드가 아니라 **실제 결과**를 확인한다(수집·통과·스킵 개수, 산출물 내용). 의심되면 일부러 깨뜨려 보거나 되돌려 false pass를 배제한다.
- 서브에이전트·사용자·나 자신의 주장도 기본값으로 신뢰하지 않고 코드·원문에 대조해 재검증한다. 수치·인용에는 출처 등급을 붙인다: `[검증됨]`(직접 확인) / `[원문]`(출처 그대로) / `[미검증]`(확인 못 함).
- 열린(open-ended) 과제는 착수 전에 단계 계획과 판정 기준(승격/보류/기각)을 정하고, 결론을 무너뜨릴 수 있는 단 하나의 질문을 먼저 답한다.
- 결과물에는 "이 작업이 답하지 못한 것"을 함께 적는다. 아무것도 못 찾은 점검도 비용이지 성공이 아니다.

## 최소 변경 (Surgical Changes)
- 과제와 무관한 인접 코드·주석·포맷은 "겸사겸사" 고치지 않는다.
- 무관한 죽은 코드는 **언급만** 하고, 삭제는 요청받았을 때만 한다. 내 변경이 만들어 낸 고아(import·변수·함수)만 정리한다.
- 자기 점검: 바뀐 모든 줄이 사용자의 요청으로 직접 거슬러 올라가야 한다.

## Git worktree
- **Chromium 개발 시 worktree를 절대 사용하지 않는다.** superpowers:using-git-worktrees 등이 worktree를 제안하더라도 chromium 대상에서는 예외 없이 금지한다.

<!-- CODEGRAPH_START -->
## CodeGraph

In repositories indexed by CodeGraph (a `.codegraph/` directory exists at the repo root), reach for it BEFORE grep/find or reading files when you need to understand or locate code:

- **MCP tool** (when available): `codegraph_explore` answers most code questions in one call — the relevant symbols' verbatim source plus the call paths between them, including dynamic-dispatch hops grep can't follow. Name a file or symbol in the query to read its current line-numbered source. If it's listed but deferred, load it by name via tool search.
- **Shell** (always works): `codegraph explore "<symbol names or question>"` prints the same output.

If there is no `.codegraph/` directory, skip CodeGraph entirely — indexing is the user's decision.
<!-- CODEGRAPH_END -->
