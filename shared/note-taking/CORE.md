# 공통 note-taking 규칙

이 문서는 Claude와 Hermes가 함께 사용하는 PKM 규칙의 단일 참조다. 플랫폼별 SKILL.md는 이 규칙을 먼저 읽고, 도구 호출 방식과 플랫폼별 연결만 얇게 덧붙인다. 두 문서 사이에 충돌이 있으면 이 문서가 우선한다.

## 1. 설정과 경계

- 실제 vault 루트·노트·미디어·위키·감사 로그 경로는 각 플랫폼의 설정 파일에서 읽는다. 사용자별 절대 경로를 본문에 하드코딩하지 않는다.
- vault 루트 밖에는 쓰지 않는다.
- 사람 존(`1-inbox/`, `2-journal/`, `3-projects/`, `4-areas/`)은 소유권을 침범하지 않는다. daily note는 지정된 에이전트 로그 섹션만 편집한다.
- 에이전트가 만드는 일반 노트와 미디어 노트는 설정된 에이전트 존(`6-agents/notes`, `6-agents/media`)에 둔다. 작성자는 frontmatter의 `author`로 구분한다.
- 지식 존(`5-wiki/`)은 전 에이전트가 읽고 쓰되, 원본 raw는 불변으로 취급하고 정합성은 위키 규칙에 따른다.

## 2. 파일 작업

- 새 Markdown 파일은 먼저 중복을 검색한 뒤 생성한다.
- 기존 파일은 먼저 읽고 필요한 부분만 patch한다. 전체 덮어쓰기로 사람의 내용을 잃지 않는다.
- 검색은 파일명과 내용을 분리해 수행한다.
- vault 안에서 `rm -rf`를 사용하지 않는다. 이동은 archive 규칙을 따르고, 삭제가 필요하면 범위를 먼저 확인한다.
- credential, password, token, API key의 값을 노트·로그·문서에 복사하지 않는다. 필요하면 변수명만 기록하거나 `[REDACTED]`로 표시한다.

## 3. 노트 메타데이터와 이력

- `6-agents/notes` 노트는 최소한 `author: claude | codex | grok | hermes`를 포함한다.
- 생성/수정 시 현재 KST 시각을 실제 명령으로 확인한다. 시각을 추측하지 않는다.
- 사람이 직접 요청한 새 노트·편집은 파일 하단 `## History`에 최신 항목을 추가하고 `6-agents/state/changelog/{YYYY-MM}.md`에도 기록한다.
- 반복 cron 갱신은 노트 본문 History를 오염시키지 않고 감사 로그에만 기록한다.
- daily note 백링크는 설정된 Hermes 작업 로그 섹션의 알맞은 날짜/시간대에만 추가하며, 기존 사람이 쓴 섹션은 보존한다.

## 4. 위키 공통 규칙

위키 작업 전 다음을 읽는다.

1. `SCHEMA.md`
2. `index.md`
3. `log.md`의 최신 항목
4. 주제와 관련된 기존 페이지

- 위키 페이지는 SCHEMA의 frontmatter와 태그 taxonomy를 따른다.
- 페이지 생성은 2개 이상 소스에 반복되거나 한 소스에서 핵심인 경우로 제한한다.
- 페이지당 outbound `[[wikilink]]`를 최소 2개 유지하고, 새 페이지는 `index.md`에 등재한다.
- 위키 작업은 `5-wiki/log.md`에 기록하고, 일반 vault 변경 감사는 `6-agents/state/changelog/{YYYY-MM}.md`에 별도로 기록한다.
- `raw/` 원본과 원본 frontmatter/hash는 임의로 수정·삭제하지 않는다. 정정은 컴파일된 페이지에 기록한다.
- APPLY 게이트가 있는 review 노트는 체크와 사용자의 처리 요청 전까지 위키 본문을 변경하지 않는다.

## 5. 플랫폼 어댑터의 책임

- Claude adapter: Claude의 Read/Edit/Grep/Write 및 `~/.claude` 설정·수동 폴백 흐름을 연결한다.
- Hermes adapter: Hermes의 file/search/patch 도구, 같은 폴더의 `config.yaml`, `note_dir`·`wiki_dir`·cron 흐름을 연결한다.
- adapter에 공통 규칙을 새로 복사하지 않는다. 공통 규칙을 바꾸면 이 파일만 수정하고 양쪽 adapter의 도구 차이만 검증한다.
