---
name: hermes
description: |
  Obsidian PKM vault 관리 + llm-wiki 지식 베이스 스킬 (Hermes 전용).
  노트 생성/편집/검색, Daily Journal 백링크, PR 문서화, 책/영화 노트(TMDB),
  그리고 소스를 컴파일하는 상호연결 위키(ingest/query/lint) 운영.
  vault·위키 경로 등 환경별 설정은 같은 폴더의 config.yaml에서 읽는다.
  트리거: "pkm" 키워드, "노트 작성/추가/편집" 요청, "저널에 기록" 요청,
  PR URL/번호 언급 + 문서화 요청, "vault에서 찾아줘" 검색,
  "책 추가", "영화 추가", "book", "movie", "읽은 책", "본 영화" 등 도서/영화 노트 생성 요청,
  "위키", "wiki", "지식베이스", "ingest", "이 소스 정리/추가", "위키에 넣어줘",
  "위키 lint/감사/점검", 위키 도메인 관련 질문 시.
version: 1.0.0
author: Hermes Agent + Amos
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [pkm, obsidian, knowledge-base, notes, markdown, journal]
    category: note-taking
    related_skills: [obsidian, llm-wiki]
---

# Hermes PKM Skill — Obsidian Vault 관리

사용자의 Obsidian vault 작업(노트 작성/편집/검색, 저널 백링크, PR 문서화, 책/영화)을 수행한다.
이 스킬은 Claude Code의 `pkm` 스킬과 동일한 PKM 규칙을 따르되, **Hermes 생성물은 전용 폴더에 격리**하고
**모든 경로를 `config.yaml`에서 읽는다**(머신마다 경로가 달라도 config만 바꾸면 동작).

## 0. 설정 로드 (모든 작업 전 필수)

**작업 시작 전 반드시 이 스킬 폴더의 `config.yaml`을 `read_file`로 읽는다.**
경로를 본문에 하드코딩하지 말고 config 값을 사용한다.

`config.yaml` 키:

| 키 | 의미 |
|----|------|
| `vault_path` | vault 루트 절대 경로 (이 하위에서만 작업) |
| `note_dir` | Hermes 일반/PR 노트 폴더 (vault 상대, 기본 `hermes/notes`) |
| `media_dir` | 책/영화 노트 폴더 (vault 상대, 기본 `hermes/media`) |
| `wiki_dir` | llm-wiki 루트 폴더 (vault 상대, 기본 `hermes`) — SCHEMA/index/log/raw/entities/… 가 여기 산다 |
| `journal_glob` | daily note 경로 패턴, `{date}`=YYYY-MM-DD |
| `journal_logs_heading` | daily note 내 Hermes 작업 백링크 섹션 헤딩 |
| `journal_time_buckets` | morning_end / afternoon_end (시간대 버킷 경계) |
| `daily_template` | daily note 없을 때 참고할 stub 템플릿 (vault 상대) |
| `history_log` | 통합 변경 이력 파일 (vault 상대, 기본 `wiki/log.md`) |
| `history_log_heading` | 이력 파일 최상단 헤딩 (이 아래에 최신 항목 삽입) |
| `wiki_schema` / `wiki_index` / `wiki_log` | 위키 SCHEMA/index/log 경로 (vault 상대) |
| `timezone` | 시각 기준 (기본 Asia/Seoul) |

**경로 우선순위**: 환경변수 `HERMES_VAULT_PATH`가 있으면 그것을 `vault_path`로 우선 사용,
없으면 `config.yaml`의 `vault_path`를 쓴다. 빠른 확인:

```bash
# 이 스킬 폴더의 config.yaml. 스킬이 다른 경로에 설치돼 있으면 그 폴더의 config.yaml을 쓴다.
CFG="$(dirname "$0")/config.yaml"   # 또는 skill_view가 알려주는 이 스킬의 절대 경로 하위 config.yaml
[ -f "$CFG" ] || CFG=~/.hermes/skills/note-taking/hermes/config.yaml
VAULT="${HERMES_VAULT_PATH:-$(grep -E '^vault_path:' "$CFG" | sed -E 's/^vault_path:[[:space:]]*//')}"
echo "VAULT=$VAULT"
```

> config.yaml은 이 SKILL.md와 **같은 폴더**에 있다. `skill_view(name='hermes')`가 반환하는
> 스킬 디렉토리 경로 하위의 `config.yaml`을 `read_file`로 읽으면 된다(경로 하드코딩 회피).

이하 설명에서 `{vault}` = 위 `vault_path`, `{note_dir}`·`{media_dir}` 등은 config 값으로 치환한다.

## Vault 작업 원칙

> [!CRITICAL] 절대 경로 — 반드시 준수
> - 모든 파일 작업은 `{vault}` 하위에서만 수행한다.
> - **Hermes가 만드는 모든 노트는 사람 노트 / 다른 에이전트(`5. Claude/` 등)와 섞지 않고
>   config의 `note_dir`·`media_dir`(기본 `hermes/`) 아래에만 둔다.**
> - 다른 PARA 폴더(`0. Inbox`, `1. Projects`, `2. Areas`, `3. Resources` 등)에 직접 쓰지 않는다.

| 종류 | 위치 |
|------|------|
| 일반 노트 / PR 문서 | `{vault}/{note_dir}/` |
| 책/영화 노트 | `{vault}/{media_dir}/` |
| Daily Journal 백링크 | `{vault}/{journal_glob}`의 `journal_logs_heading` 섹션 (백링크만; 노트 본체는 위 폴더에) |

## 도구 사용 규칙

- 새 노트: `write_file`로 절대 경로에 생성(폴더 없으면 자동 생성). **파일명과 같은 H1은 쓰지 않는다**.
- 기존 노트 편집: 먼저 `read_file`로 읽고 `patch`로 해당 위치만 수정(기존 보존, 중복 방지).
- 검색: `search_files`(내용/파일명). 공백 포함 경로 주의(예: `1. Daily`).
- vault `.md`를 만들거나 고칠 때는 **항상 아래 "변경 이력" 규칙**(노트 하단 `## History` + config의 `history_log`)을 따른다.

## 공통 규칙: frontmatter 시간

`created`/`modified`/`date`/History 시각은 추측 금지 — `terminal`로 실제 시각 확인:

```bash
date '+%Y-%m-%d %H:%M:%S'   # created/modified
date '+%Y-%m-%d'            # date
date '+%Y-%m-%d %H:%M'      # History 항목
```
- 생성 시: `created` = `modified` = 현재 시각
- 편집 시: `modified`만 현재 시각으로 갱신
- 시간대는 config의 `timezone`(기본 Asia/Seoul) 기준

태그 규칙(최소):
- base 태그 정확히 1개: `work` | `personal` (업무 repo→work, 개인→personal)
- 주제 태그: feature/fix/refactor/docs/chore/troubleshooting/planning/dev/book/movie 등에서 적절히
- 파일명: 한글 자연어, 특수문자(`/\:*?"<>|#`)→`-`, 최대 100자

## 공통 규칙: superpowers 작업 문서 참고

work 노트·PR 문서를 만들 때 그 작업의 repo에 superpowers 산출물이 있으면 참고해 맥락을 보강한다.
- 위치: `<repo>/docs/superpowers/specs/*.md`(설계)·`<repo>/docs/superpowers/plans/*.md`(구현 계획). cwd가 아니라 **그 작업의 repo 루트** 기준.
- 활용: 관련 문서만 읽어 `# 목적`·`## 기술적 고려사항`(PR 노트는 `## 기술적 의사결정`)의 "왜"를 보강.
- 출처: 참고한 문서는 `# 참고`(PR 노트는 `## 참고`)에 repo-상대경로로 남긴다.
- gitignore된 로컬 산출물이라 없을 수 있다 → 있을 때만 쓰고 없으면 조용히 건너뛴다.

```bash
ls "$REPO"/docs/superpowers/specs/*.md "$REPO"/docs/superpowers/plans/*.md 2>/dev/null
```

상세 노트 구조는 `references/note-template.md`를 참고한다.

## 통합 구조: PKM 노트 + llm-wiki (한 폴더)

`hermes/` 한 폴더가 두 레이어를 함께 담는 **단일 PKM 시스템**이다(사용자 요청으로 merge).

| 레이어 | 위치 | 역할 |
|--------|------|------|
| PKM 노트 | `hermes/notes`, `hermes/media` | 작업/PR/책/영화 등 개별 노트(이 SKILL.md의 1~6절) |
| llm-wiki | `hermes/SCHEMA.md`·`index.md`·`log.md`·`raw/`·`entities/`·`concepts/`·`comparisons/`·`queries/` | 소스를 컴파일한 상호연결 지식 베이스(도메인 PKM) |

- llm-wiki 레이어의 ingest/query/lint 절차·SCHEMA·frontmatter 규칙은 `[[llm-wiki]]` 스킬을 그대로 따른다. **단, WIKI 경로는 `WIKI_PATH` 기본값이 아니라 이 vault의 `hermes/`**(아래 config `wiki_dir`)다.
- llm-wiki의 `hermes/log.md`(작업 로그)는 obsidian-history의 `wiki/log.md`(변경 로그)와 **경로·용도가 완전히 별개** — 헷갈리지 말 것.
- 어떤 입력이 "개별 노트"인지 "위키 페이지(2+ 소스/핵심)"인지는 SCHEMA의 Page Thresholds로 판단: 스쳐가는 건 노트, 반복·핵심이면 위키 페이지로 승격.

---

## 1. 노트 생성

위치: `{vault}/{note_dir}/<제목>.md`. `write_file`로 생성. `references/note-template.md`의 **A. 일반/work 노트** 구조 사용.
단순 메모는 `# 작업 내용`/`# 결과`/`# 참고`를 상황에 맞게 생략 가능. work 노트는 전체 구조를 따른다.
생성 후 아래 "변경 이력" 규칙에 따라 노트 `## History`와 `history_log`에 기록한다.

## 2. 노트 편집

1. `read_file`로 기존 내용 확인
2. `patch`로 해당 부분만 수정(기존 보존, 중복 방지)
3. frontmatter `modified` 갱신
4. `## History`에 항목 추가 + `history_log` 기록 (아래 "변경 이력")

## 3. 노트 검색

- 내용 검색: `search_files`(`target=content`, `path={vault}`, `file_glob="*.md"`)
- 파일명/폴더: `search_files`(`target=files`, 예 `pattern="*.md"`, `path="{vault}/{note_dir}"`)
- 결과를 사용자에게 목록으로 제시

---

## 4. Daily Journal 백링크

### 위치
config의 `journal_glob`에서 `{date}`를 대상 날짜로 치환: `{vault}/Retrospective/1. Daily/YYYY-MM-DD.md`

### 시간대 판단
- 00:00~05:59 (새벽) → **전날** 날짜의 Evening (아직 안 잔 것으로 간주)
- 06:00~11:59 → 당일 Morning / 12:00~17:59 → Afternoon / 18:00~23:59 → Evening
  (경계는 config `journal_time_buckets`의 morning_end / afternoon_end 사용)

### 절차
1. 대상 daily note를 `read_file`로 읽는다.
2. `journal_logs_heading` 섹션(기본 `## 🤖 Hermes 작업 로그`)의 해당 `### Morning/Afternoon/Evening` 아래에 `- [[노트 제목]]`을 `patch`로 삽입.
   - 이미 같은 백링크가 있으면 스킵(멱등). 시간대 헤딩이 없으면 만든다.
   - `journal_logs_heading` 섹션 자체가 없으면 daily note **맨 끝**에 새로 만들고 그 아래 추가(사람이 쓴 다른 섹션은 건드리지 않는다).
3. daily note 파일이 없으면 config의 `daily_template`을 참고해 stub을 만든 뒤 추가.
4. daily note는 사람 파일이므로 편집 후 "변경 이력" 규칙(`## History` + `history_log`)을 적용한다.

---

## 5. PR 문서화

GitHub PR을 work 노트로 변환해 **`{vault}/{note_dir}/`**에 기록한다. `references/note-template.md`의 **B. PR 문서화 노트** 구조 사용.
repo에 superpowers spec/plan이 있으면 "공통 규칙: superpowers 작업 문서 참고"에 따라 `## 기술적 의사결정`을 보강하고 `## 참고`에 경로를 남긴다.

### PR 정보 수집
- **URL 제공 시**: `gh pr view {url} --json ...`
- **번호만 제공 시**: 현재 repo 기준 `gh pr view {번호}`. 모호하면 사용자에게 repo 확인.

### 파일명 규칙
- `{repo} - PR{번호} - {설명}` 형식. repo 이름은 `gh pr view --json headRepository --jq '.headRepository.name'`(kebab-case 그대로).
- frontmatter `repository:` 필드와 같은 값. `#` 금지, `feat:`/`fix:` prefix 제거(태그로 표현), 특수문자→`-`.

PR 타입 → 주제 태그: feat/feature→feature, fix→fix, refactor→refactor, docs→docs, chore/build/ci/test→chore, troubleshoot/debug→troubleshooting, plan/design→planning, 판단 불가→feature.

생성 후 노트 `## History`와 `history_log`에 한 줄 기록.

---

## 6. 책/영화 노트

위치: **`{vault}/{media_dir}/<제목>.md`**. `references/note-template.md`의 **C. 영화** / **D. 책** 구조 사용.

### 제목 확인
입력에서 제목 추출(예: "오펜하이머 영화 추가" → `오펜하이머`). 알 수 없으면 `clarify`로 묻는다.

### 중복 확인
`search_files`로 `{media_dir}`에 동일 제목 파일이 있으면 알리고 중단.

### TMDB 자동완성 (영화/TV, 선택)
환경변수 `$TMDB_API_KEY`가 있으면 메타데이터를 자동으로 채운다. **키가 없으면 TMDB를 건너뛰고** cover 등을 빈 채로 생성(하드코딩 금지).

```bash
curl -s "https://api.themoviedb.org/3/search/movie?api_key={KEY}&query={제목}&language=ko-KR"
# TV: .../search/tv?...
```
- 첫 결과 사용. `poster_path`→`cover: https://image.tmdb.org/t/p/w500/{poster_path}`, `release_date`→`release_year`(연도), `genre_ids`→`genre`(한글 변환).
- 한글 검색 실패 시 `original_title`로 재시도. 감독/출연: `/movie/{id}/credits`에서 `job:"Director"`→director, `cast` 상위 3~5→actor.

TMDB 장르 ID→한글: 28 액션, 12 모험, 16 애니메이션, 35 코미디, 80 범죄, 99 다큐멘터리, 18 드라마, 10751 가족, 14 판타지, 36 역사, 27 공포, 10402 음악, 9648 미스터리, 10749 로맨스, 878 SF, 53 스릴러, 10752 전쟁, 37 서부, 10770 TV 영화.

책은 저자·장르 등 추가 정보 제공 시 기입. cover는 웹 검색으로 채울 수 있음(선택).
생성 후 노트 `## History`와 `history_log`에 한 줄 기록.

---

## 변경 이력 규칙 (obsidian-history 호환)

vault 내 `.md`를 만들거나 고칠 때마다 **두 곳**에 이력을 남긴다.

### 1) 파일 하단 `## History`
- 본문 마지막과 History 사이는 **빈 줄 2개 + `---`**로 구분.
- 이미 `## History`가 있으면 헤딩 바로 아래(기존 항목 위)에 삽입 → **최신이 맨 위**.
- 없으면 파일 맨 끝에 `---` + `## History`로 새로 만든다. 기존 항목은 수정/삭제 금지.
- 형식: `- YYYY-MM-DD HH:MM 변경 내용 한 줄 요약`

### 2) 통합 로그 (config `history_log`, 기본 `{vault}/wiki/log.md`)
- `history_log_heading`(기본 `# Change Log`) 바로 아래에 새 줄 삽입 → **최신이 맨 위**.
- 형식: `- YYYY-MM-DD HH:MM \`vault 루트 기준 상대 경로\` — 변경 내용 요약`
- **예외**: `history_log` 자체를 수정할 때는 거기에 중복 기록하지 않는다(파일 내 History만).

### 적용 범위
- 대상: `{vault}/` 하위 모든 `.md`
- 새 파일 최초 생성 시 History 첫 항목은 "최초 생성 (hermes)".
- 요약은 한국어, 한 줄, 무엇이/왜 바뀌었는지 핵심만. 여러 변경은 쉼표로 한 줄에.

---

## 7. llm-wiki — 지식 베이스 (ingest / query / lint)

`hermes/`(config `wiki_dir`)에 사는 상호연결 위키. 소스를 한 번 컴파일해두고 최신으로 유지한다.
RAG와 달리 교차참조·모순·종합이 이미 페이지에 반영돼 있다. 도메인은 `wiki_schema`(SCHEMA.md) 참조.

> [!CRITICAL] 위치/충돌 주의
> - 위키 루트 = `{vault}/{wiki_dir}`. 위키 작업 로그는 `wiki_log`(`hermes/log.md`)이며
>   **obsidian-history의 `history_log`(`wiki/log.md`)와 별개**다. 둘을 혼동하지 않는다.
> - `raw/` 안의 원본 소스는 **불변**. 수정/삭제하지 않는다(정정은 위키 페이지에).

### 7.0 오리엔테이션 (위키 작업마다 먼저)
ingest/query/lint 전에 항상 순서대로 읽어 자신을 맞춘다(중복 페이지·누락 링크 방지):
1. `read_file` `wiki_schema` — 도메인·규칙·태그 taxonomy 파악
2. `read_file` `wiki_index` — 어떤 페이지가 있는지
3. `wiki_log` 최근 20~30줄 — 최근 활동
4. (페이지 많으면) 다룰 주제로 `search_files`(`path={vault}/{wiki_dir}`, `file_glob="*.md"`) 먼저

### 7.1 Ingest (소스 추가)
① 원본 캡처: URL→`web_extract`로 마크다운 받아 `raw/articles/`에, PDF→`raw/papers/`, 붙여넣기→적절한 `raw/`.
   **`web_extract`/browser가 안 되면**(예: browser navigate가 `Library not loaded: libicui18n` 등 dylib 불일치로 실패) `references/article-extraction-fallback.md`의 curl+Python 레시피로 본문을 받아 동일하게 raw에 저장한다.
   서술적 파일명. raw frontmatter(`source_url`/`ingested`/`sha256` 본문 해시) 추가. 같은 URL 재수집 시 sha256 비교(동일=스킵, 다르면 드리프트 표시+갱신).
② (대화형) 핵심 takeaway를 사용자와 짚는다. (자동/cron은 생략하고 바로 진행)
③ 기존 확인: index.md + `search_files`로 언급된 엔티티/개념 페이지가 이미 있는지. (중복 vs 성장의 분기점)
④ 페이지 작성/갱신: SCHEMA의 Page Thresholds 충족 시에만 생성. 기존 페이지엔 정보 추가 + `updated` 갱신. 모순 시 Update Policy. **페이지당 `[[wikilinks]]` 최소 2개**. 태그는 taxonomy에서만. 3+ 소스 종합 페이지엔 `^[raw/...]` provenance. 단일/의견성 주장은 `confidence: medium|low`.
⑤ 네비 갱신: 새 페이지를 index.md 올바른 섹션(가나다/알파벳)에 추가, header의 Total/Last updated 갱신. `wiki_log`에 `## [날짜] ingest | 제목` + 생성/수정 파일 나열.
⑥ 변경 보고: 만든/고친 파일 전부 사용자에게.
   한 소스가 5~15개 페이지를 건드릴 수 있다(정상, 복리 효과). 10개+ 페이지를 건드릴 ingest는 먼저 범위를 사용자와 확인.

> [!TIP] 대량(30개+) 일괄 ingest
> Readwise export·웹 스크랩 폴더 등 수십~수백 개를 한꺼번에 정리할 땐 `references/bulk-source-ingest.md`의 절차를 따른다:
> raw 흡수(execute_code) → 메타데이터만으로 클러스터링 → subagent 동시 3개씩 배치로 병렬 컴파일 → 부모가 검증(깨진 링크/고아/taxonomy)·index/log 통합. 한 턴에 다 합성하려 하지 말 것.

> **기존 노트 대량(100+) 정리**: Readwise/Bear 익스포트 등 이미 vault에 있는 수백 개 노트를 위키로 옮길 땐 `references/bulk-import-existing-notes.md` 참고. 핵심: "복사 ≠ 컴파일"을 먼저 합의 → raw 흡수(execute_code 한 번, `open()` 사용; `hermes_tools.read_file`는 KeyError 위험) → 메타데이터만으로 클러스터링(과대 클러스터는 재분할) → `delegate_task` 동시 3개 fan-out(각 subagent에 형식 규칙·taxonomy 전체를 context로 박고, index/log는 건드리지 말라고 지시) → 배치마다 직접 검증(자기보고 불신, 데드링크 대소문자 주의) → 부모가 index/log 통합.

### 7.2 Query (위키에 질문)
① index.md로 관련 페이지 식별 → (100+ 페이지면) `search_files`로 핵심어 보강 → 관련 페이지 `read_file`.
② 컴파일된 지식으로 답을 종합하고 인용: "[[페이지A]]·[[페이지B]] 기준…".
③ 재도출이 아까운 실질적 비교/심층/종합 답이면 `queries/` 또는 `comparisons/`에 페이지로 보관(사소한 조회는 보관 안 함).
④ `wiki_log`에 query + 보관 여부 기록.

### 7.3 Lint (점검/감사)
`execute_code`로 `{vault}/{wiki_dir}` 하위 `.md`를 스캔해 보고(심각도순):
- 깨진 `[[wikilink]]`(대상 페이지 없음) / orphan(인바운드 링크 0) / index 누락(파일 vs index 대조)
- frontmatter 필수필드 누락, taxonomy 밖 태그 / `contested:true`·`confidence:low` 검토 목록
- source drift(`raw/`의 sha256 재계산 불일치) / 200줄 초과(분할 후보) / stale(updated가 관련 최신소스보다 90일+ 오래)
- 로그 rotation(`wiki_log` 500항목+)
보고 후 `wiki_log`에 `## [날짜] lint | N issues found`.

### 7.4 Obsidian 호환
이 위키는 그대로 Obsidian 볼트로 열린다: `[[wikilinks]]`·Graph View·Dataview(frontmatter)·`raw/assets/` 이미지(`![[img.png]]`).

### 7.5 대량 import — 기존 Obsidian export 폴더를 위키화 (Readwise/Bear 등)
사용자가 "기존 노트를 위키로 정리/복사"를 요청할 때(예: `Readwise/Articles`, `Bear/` 등 수십~수백 개). 상세 레시피는 `references/bulk-import-readwise.md` 참고. 핵심:

- **"복사"는 위키 플로우가 아니다 — 먼저 성격을 판별한다.** Readwise/클리핑류는 외부 글의 하이라이트 발췌 = **레이어1 raw 소스**(작성자 본인 정리가 아님). 그냥 `concepts/`로 복붙하면 레이어가 섞이고 교차참조·종합이 사라진다. → `raw/`로 흡수 후 *컴파일*해야 한다.
- **2단계로 쪼갠다.** (1) **Import**(기계적·안전): 전체를 `raw/articles/`로 복사 + raw frontmatter(`source_url`/`ingested`/`sha256`) 부착, 원본 export 폴더는 **보존**. (2) **Compile**(점진·판단): raw를 주제 클러스터로 묶어 `concepts/` 페이지 합성. 한 턴에 200개를 다 컴파일하지 말 것 — 품질·컨텍스트가 무너진다.
- **파일럿 먼저.** 전체 컴파일 전에 한 주제(10~15개)만 끝까지(import→concept) 돌려 사용자에게 형식·묶음 품질을 확인받고 확장한다.
- **대량 컴파일은 subagent 병렬.** 메타데이터(Title/Summary)만 뽑아 클러스터링 → 클러스터별 파일 리스트를 `/tmp/`에 떨궈 `delegate_task`(toolsets=['file'])로 동시 3개씩 처리. 각 subagent에 SCHEMA 규칙(frontmatter/wikilink 2+/blockquote 하이라이트/URL 명시)을 context로 박고, **index.md·log.md는 건드리지 말라**고 지시 → 부모가 결과를 받아 통합.\n- **배치마다 부모가 직접 검증(자기보고 불신)** + **배치 간 orphan은 부모가 cross-link로 메운다** + **index.md는 전면 재생성**(append 아님). 데드링크 대소문자 불일치 주의. 상세는 `references/bulk-import-readwise.md` 5~7절.
- **하이라이트 강조 형식**(사용자 선호): concept 페이지에서 각 소스 섹션은 `출처: [제목](URL)` 명시 + 핵심 하이라이트를 blockquote(`>`)로 인용. 원문 URL은 frontmatter `sources:`뿐 아니라 본문에도 직접 노출.

---

## 에러 처리
| 상황 | 처리 |
|------|------|
| 파일 미존재 | `write_file`로 새로 생성 |
| 섹션 미존재 | 해당 섹션을 만들어 추가 |
| 중복 백링크 | `read_file`로 확인 후 있으면 스킵 |
| PR 미발견 | 에러 메시지 출력 |
| TMDB 키 없음 | TMDB 건너뛰고 빈 메타로 생성 |
| config.yaml 없음/경로 불명 | 사용자에게 `vault_path` 확인 요청 |
| 위키 페이지 임계 미달 | 페이지 생성하지 않고 기존 페이지에 통합하거나 보류 |
| `raw/` 수정 시도 | 금지 — 원본 불변, 정정은 위키 페이지에 |

## 의존성
- `read_file` / `patch` / `write_file` / `search_files` / `terminal` (vault 파일 직접 조작)
- `gh` CLI (PR 문서화 시)
- `web_extract` (위키 ingest 시 URL/PDF 캡처) — 불가 시 `references/article-extraction-fallback.md`(curl+Python)로 우회
- `execute_code` (위키 lint 스캔)
- (선택) `$TMDB_API_KEY` (책/영화 메타데이터)

## Pitfalls
- **경로를 본문에 하드코딩하지 말 것** — 항상 `config.yaml`(또는 `HERMES_VAULT_PATH`)에서 읽는다.
- **Hermes 생성물은 `note_dir`/`media_dir` 밖으로 나가지 않는다** — 사람/타 에이전트 영역 오염 금지.
- **시각은 `date`로 확인** — 추측 금지.
- **`raw/`나 사람 노트를 임의 수정하지 않는다** — daily note 등 사람 파일은 지정된 섹션만 건드린다.
- **이력 누락 금지** — vault `.md` 변경 시 `## History` + `history_log` 둘 다 기록.
- **위키 로그 ≠ 변경 이력 로그** — llm-wiki 작업은 `wiki_log`(`hermes/log.md`)에, obsidian-history 변경은 `history_log`(`wiki/log.md`)에. 혼동 금지.
- **`raw/`는 불변** — 위키 원본 소스는 수정/삭제하지 않는다. 정정은 위키 페이지에서.
- **고립 페이지 금지** — 위키 페이지는 `[[wikilinks]]` 최소 2개로 연결. index.md·log.md 갱신 누락 금지.
- **vault root 경로 주의** — 이 vault의 실제 root는 config.yaml의 `vault_path` 기준이며 `amoseui`가 두 번 중첩된 구조다. Claude Code의 `pkm` 스킬은 한 단계 위로 잘못 적혀 있으니 그 값을 그대로 베끼지 말 것. 정확한 root는 `obsidian-history` 스킬과 이 스킬의 config.yaml 기준.
- **config 값 파싱은 YAML 파서로** — config.yaml 값에 인라인 주석(`키: 값  # 설명`)을 쓰면 셸 `grep|sed` 같은 단순 파서가 주석까지 값으로 잡아 `hermes/notes  # ...` 같은 깨진 경로 폴더를 만든다(이 세션에서 실제 발생). 값 검증/사용은 `read_file`로 YAML을 읽어 처리하고, config.yaml에는 인라인 주석을 두지 않는다(설명은 키 위 줄에).
- **`media_dir` 값의 `/`는 중첩 폴더가 된다** — 위 파싱 사고로 `책/영화 노트` 같은 값이 폴더로 만들어지면 `/` 때문에 중첩 디렉토리가 생긴다. 잘못 만든 빈 폴더 정리는 `rm -rf`가 아니라 안쪽→바깥쪽 순서로 `rmdir`(비어있을 때만 삭제)를 써서 데이터 손실 위험 없이 지운다.
- **vault 안 정리는 `rm -rf` 금지(사용자 규칙)** — 이 사용자는 vault에서의 `rm -rf` 실행을 거부했다. 잘못 만든 항목 정리는 항상 빈 폴더만 지우는 `rmdir`(또는 개별 파일 `rm -f`)를 쓰고, 비어있지 않으면 먼저 내용을 사용자에게 확인한다. 재귀 강제 삭제는 제안하지 않는다.
- **`execute_code`의 `from hermes_tools import read_file`는 SKILL.md의 Read 툴과 반환형이 다르다** — hermes_tools 래퍼는 `["content"]` 키를 보장하지 않아 `KeyError: 'content'`가 난다(이 세션 실제 발생). execute_code 안에서 vault 파일을 대량으로 읽거나 raw로 복사할 때는 그냥 파이썬 stdlib(`open(...).read()`)을 쓰는 게 안전하다. 파일 IO·해시·복사는 stdlib로, 위키 페이지 *생성*만 write_file 류로.
- **대량 import는 "복사"가 아니라 raw 흡수 후 컴파일** — 7.5절 참고. 기존 export 폴더(Readwise 등)를 통째로 `concepts/`에 복붙하지 말 것. 외부 클리핑은 레이어1 raw다.
