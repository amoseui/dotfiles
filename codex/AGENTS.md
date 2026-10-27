# Global Codex guidance

- 사용자에게 한국어로 응답하고, 기술 용어·코드 식별자는 원문을 유지한다.
- 코드 주석과 커밋 메시지는 영어로 작성한다. 커밋 형식·포맷·빌드·검증 명령은 해당 저장소의 규칙을 따른다.
- Chromium 커밋 제목은 `cl-description` 스킬 형식에 맞춰 `[webauthn] ...`처럼 소문자 모듈 태그를 우선한다.
- Gerrit 업로드 전에 커밋 설명의 제목·본문·footer 줄바꿈을 72자 기준으로 확인한다. 설명 서식만 수정하기 위한 재업로드로 message-only patchset을 만들지 않는다.
- Chromium 커밋 메시지에는 `Test:` footer를 작성하지 않는다. `cl-description` 등 스킬·템플릿에서 요구하더라도 이 사용자 규칙을 우선한다. 필요한 테스트와 검증은 수행하고, 결과는 작업 보고에 남긴다.
- Git 개발 브랜치를 새로 만들 때는 생성일(사용자 로컬 시간대)의 `YYMMDD-`를 이름 맨 앞에 붙인다(예: `260912-cssstylerule-inherits-grouping-rule`). 날짜는 브랜치 생성 시점에 확인한다.
- API 토큰 등 비밀값을 직접 읽거나 명령에 주입받지 않는다. 설정 파일·`.env`·비밀 저장소 CLI에서 값을 꺼내거나 출력·파일로 복사하지 않는다. 토큰이 필요한 데이터는 정해진 수집기 명령(`collect <source>`)과 그 출력 파일로만 쓰고, 없으면 사용자에게 묻는다.
- 수집 데이터는 `~/.local/share/collectors/<source>/`에 있고 형식은 `~/Workspace/github/collectors/README.md`를 따른다. `collected_at`이 오래됐으면 `collect <source>`를 한 번 실행한 뒤 읽는다.
- 사실과 추정을 구분하고, 완료·통과를 보고하기 전에 실제 결과와 산출물을 확인한다. 검증하지 못한 범위도 명시한다.
- 요청과 직접 관련된 범위만 수정하고, 기존 미커밋 변경을 보존한다.
- 이미 승인된 작업과 가역적인 수정은 계속 진행한다. 선택적인 스킬 절차 때문에 같은 허가를 반복해서 묻지 않는다.
- Chromium 개발에서는 저장소 규모 때문에 git worktree를 만들지 않는다.
- 스킬에 Claude의 `Read/Edit/Write/Bash/Grep/Glob`가 나오면 현재 제공된 읽기·패치·쉘·검색 도구로 대응한다. `Skill` 도구가 없으면 해당 `SKILL.md`를 직접 읽는다.
- Claude 플러그인의 `/codex:review`·`/codex:adversarial-review`는 Codex 명령이 아니다. Codex에서는 사용 가능한 review 기능이나 독립 검토자를 쓰고 실제 검토 범위를 보고한다.

## Chromium 작업 기반 확인

- Chromium 작업을 새로 시작하기 전에 저장소의 절대 경로, 현재 브랜치와 HEAD, 사용할 base 브랜치와 정확한 base commit SHA를 확인해 사용자에게 제시하고 명시적인 확인을 받는다. 확인 전에는 코드 수정이나 기반 변경을 시작하지 않는다. 같은 세션에서 동일한 기반을 이미 확인받았다면 반복해서 묻지 않는다.
- 사용자가 pull·sync·빌드를 완료한 checkout과 빌드 산출물의 소스 기반을 보존한다. 빌드 날짜만으로 최신 main 여부를 판단하거나, 기존 빌드를 재사용한다는 이유로 다른 브랜치·과거 commit을 선택하지 않는다.
- 승인된 기반을 바꾸는 rebase, checkout/switch, reset, pull, gclient sync는 임의로 실행하지 않는다. 변경이 필요하면 대상 base 브랜치와 정확한 commit SHA, 변경 이유, DEPS·기존 빌드·재빌드에 미칠 영향을 먼저 설명하고 별도 확인을 받는다. fetch와 읽기 전용 비교는 가능하지만, 그 결과를 checkout에 자동 적용하지 않는다.
- 구현 계속 진행, 충돌 해결, WIP 업로드 요청이나 빌드 완료 통보 자체를 base 변경 승인으로 해석하지 않는다. 사용자가 승인한 기반에서 필요한 수정·검증·업로드를 진행한다.
- WebRTC·V8·DevTools 등 별도 저장소의 기반 변경이 Chromium 작업이나 빌드에 영향을 주면 해당 저장소의 경로와 base commit도 함께 제시하고 확인받는다.
- 빌드·테스트 결과에는 실제 검증한 Chromium commit, 관련 별도 저장소의 commit, 빌드 디렉터리를 기록한다. 이전 기반의 통과 결과를 rebase 후 기반의 검증 결과로 보고하지 않는다.

<!-- CODEGRAPH_START -->
## CodeGraph

In repositories indexed by CodeGraph (a `.codegraph/` directory exists at the repo root), reach for it BEFORE grep/find or reading files when you need to understand or locate code:

- **MCP tool** (when available): `codegraph_explore` answers most code questions in one call — the relevant symbols' verbatim source plus the call paths between them, including dynamic-dispatch hops grep can't follow. Name a file or symbol in the query to read its current line-numbered source. If it's listed but deferred, load it by name via tool search.
- **Shell** (always works): `codegraph explore "<symbol names or question>"` prints the same output.

If there is no `.codegraph/` directory, skip CodeGraph entirely — indexing is the user's decision.
<!-- CODEGRAPH_END -->
