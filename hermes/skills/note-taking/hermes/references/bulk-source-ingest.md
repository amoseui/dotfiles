# 대량 소스 일괄 ingest — Readwise/클리핑 폴더를 llm-wiki로 컴파일

수십~수백 개의 외부 클리핑(Readwise export, 웹 스크랩 폴더 등)을 llm-wiki concept 페이지로
한 번에 정리할 때의 검증된 절차. **한 턴에 다 컴파일하려 하지 말 것** — 클러스터링 후 subagent 병렬이 정석.

## 언제 쓰나
- "이 폴더(Readwise 등) 전부 위키로 정리해줘" 같이 30개+ 소스를 ingest해야 할 때.
- 소스가 **외부 글의 클리핑/하이라이트**(= raw 레이어)인 경우. 사용자가 직접 쓴 정리 노트가 아님에 주의.

## 핵심 원칙
- **복사 ≠ ingest.** raw는 원본 그대로 보존하고, concept 페이지는 여러 소스를 *합성*한 새 글이다.
- **원본 폴더는 건드리지 않는다.** raw/로 복사만 하고 Readwise 등 원본은 그대로 둔다.
- **10개+ 건드리는 ingest는 먼저 범위를 사용자와 확인**(SCHEMA 규칙). 파일럿 1클러스터로 품질 합의 후 확장하면 안전.

## 절차

### 1단계 — raw 흡수 (기계적, execute_code 한 번)
원본 폴더의 각 `.md`를 `{wiki}/raw/articles/`(또는 `raw/books/`)로 복사하며 frontmatter 부착.
- `source_url`: 본문의 `- URL:` 라인에서 추출 (없으면 빈 값)
- `ingested`: 오늘 (TZ=Asia/Seoul date)
- `sha256`: 본문 전체(원본 그대로) 해시. 재실행 시 기존 sha와 같으면 스킵, 다르면 드리프트로 갱신.
- **read_file 래퍼는 dict 반환 형식이 달라 KeyError 남** → execute_code 안에서는 표준 `open()`으로 읽어라.

```python
import hashlib, re, os
for f in files:
    body = open(src, encoding="utf-8").read()
    url = (re.search(r'^- URL:\s*(\S+)', body, re.M) or [None,""])
    url = url.group(1) if hasattr(url,'group') else ""
    sha = hashlib.sha256(body.encode()).hexdigest()
    fm = f"---\nsource_url: {url}\ningested: {today}\nsha256: {sha}\n---\n\n"
    # 기존 파일 sha와 비교해 스킵/갱신
    open(dst,"w",encoding="utf-8").write(fm+body)
```

### 2단계 — 클러스터링 (execute_code, 메타데이터만)
모든 raw의 `Full Title` + `Summary`만 추출해 압축 출력(본문 전체를 컨텍스트에 올리지 말 것).
키워드 휴리스틱으로 주제 클러스터를 나눈다. **한 클러스터가 40개+면 너무 큼 → 의미별로 더 쪼개라.**
클러스터별 파일 리스트를 `/tmp/cl/<클러스터>.txt`로 떨군다(subagent가 읽을 입력).

전형적 클러스터 예(개발자 블로그 코퍼스): ai-coding, mindset, startup, career, team, devtech,
writing, learning, productivity, habit, retro, decision, creativity.

### 3단계 — subagent 병렬 컴파일 (delegate_task, 동시 3개씩 배치)
각 subagent에 **클러스터 1개**를 배정. 동시 최대 3개라 배치로 나눠 돌린다(작은 클러스터는 한 subagent에 2개 합쳐도 됨).
백그라운드라 배치 완료 메시지가 자동으로 돌아옴 — 폴링하지 말 것.

subagent context에 반드시 박을 것:
- raw 목록 파일 경로(`/tmp/cl/X.txt`)와 raw 디렉토리 절대경로
- 출력 위치(`{wiki}/concepts/<제목>.md`), 한글 자연어 파일명, 특수문자→`-`
- **페이지 형식**: frontmatter(title/created/updated/type:concept/tags/sources/confidence) +
  첫줄 요약 → 핵심명제 불릿 → 소스별 `출처:[제목](URL)` + 하이라이트 blockquote(>) 강조 +
  wikilink 2+ + 3소스+ 종합문단 끝 `^[raw/articles/파일.md]` + 끝에 `---` + `## History`
- **tag taxonomy 전체를 나열**(subagent는 SCHEMA를 모름). taxonomy 밖 태그 금지.
- toolsets는 `["file"]`만으로 충분.
- **금지**: index.md/log.md 수정 금지(부모가 통합), raw 수정 금지, 존재하지 않는 페이지 wikilink 금지.
- 보고: 생성 파일명 + 소스 묶음 + index 항목(`- [[페이지]] — 요약`) 표로.

### 4단계 — 검증 + 통합 (부모가 execute_code로)
subagent 자기보고는 신뢰하지 말고 **직접 스캔**한다:
- 모든 concept `.md`: frontmatter/sources/History 있는지, wikilink ≥2인지
- **깨진 wikilink**: `[[X]]` 중 실제 파일 없는 것 (대소문자 불일치 흔함 — 예 `LLM-` vs `llm-`)
- **고아 페이지**: 인바운드 링크 0 (배치 *간* cross-link이 없어 자주 생김 → 관련 허브 페이지에
  `## 관련 개념 (추가 연결)` 섹션 만들어 `[[고아]]` 링크를 넣어 해소)
- **taxonomy 밖 태그**
- **index 누락**: 모든 slug가 index.md에 있는지

통합:
- `index.md` 재생성: 각 페이지 title + 첫 본문 문단(요약) 자동 추출 → 주제 그룹별 섹션으로. Total/Last updated 갱신.
- `log.md`에 통합 ingest 한 항목 추가(소스 수, 클러스터, 생성 페이지 수, 검증 결과).

## 실전 수치 (1회 사례)
Readwise 222개(Articles 221 + Books 1) → concept 66개. 클러스터 13개, subagent 배치 4회(각 3개).
배치당 2~8분. 최종 lint: 깨진 링크 0 / 고아 0 / 형식 문제 0.

## Pitfalls
- **mindset/기타 같은 잡탕 클러스터가 비대해진다** → 2차 키워드 재분류로 회고·학습·의사결정·창의성 등으로 쪼개라.
- **배치 간 cross-link 누락** → subagent는 자기 클러스터 안에서만 링크하므로, 부모가 4단계에서 고아를 반드시 해소.
- **대소문자 깨진 링크** → 기존 페이지가 가리키는 slug와 실제 파일명 대소문자를 맞춰라.
- **중복 주제** → 파일럿에서 이미 만든 페이지(예: 습관-복리-시스템)와 겹치면, subagent에 "이미 처리됨, 제외하고 cross-link만" 명시.
- **subagent는 SCHEMA를 못 읽음** → taxonomy·형식·금지사항을 context에 통째로 박아라.
