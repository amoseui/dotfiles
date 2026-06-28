# 대량 import — 기존 Obsidian export 폴더를 llm-wiki로 컴파일

`Readwise/Articles`(221개), `Readwise/Books`, `Bear/` 등 vault 안에 이미 있는 수십~수백 개
export 노트를 위키화할 때의 검증된 절차. SKILL.md 7.5절의 상세판.

## 0. 성격 판별이 먼저
- 사용자가 "내가 정리한 지식 노트"라고 말해도, Readwise 익스포트는 실제로는 **외부 글의 하이라이트 발췌**다.
  구조: 상단 `## Metadata`(Author/Full Title/Category/Summary/URL) + `## Highlights`. → 레이어1 **raw 소스**.
- raw로 흡수 후 *컴파일*. `concepts/`에 그대로 복붙 금지(레이어 혼합, 종합/교차참조 상실).

## 1. Import (기계적·안전) — 전체를 raw/로 흡수
원본 export 폴더는 **건드리지 않고** raw/articles(또는 raw/books)로 복사 + frontmatter 부착.
재실행 안전(idempotent): 같은 파일은 sha256 비교로 스킵, 본문 바뀐 것만 갱신.

```python
# execute_code — stdlib만 사용 (hermes_tools.read_file는 ["content"] 보장 안 함 → KeyError)
import hashlib, re, os
base = "<vault>/Readwise"           # export 루트
raw_root = "<vault>/hermes/raw"
ingested = "<오늘 YYYY-MM-DD>"      # date로 확인한 값
jobs = [("Articles", os.path.join(raw_root, "articles")),
        ("Books",    os.path.join(raw_root, "books"))]

def existing_sha(p):
    if not os.path.exists(p): return None
    head = open(p, encoding="utf-8").read(600)
    m = re.search(r'^sha256:\s*([0-9a-f]+)', head, re.M)
    return m.group(1) if m else None

for sub, dst_dir in jobs:
    src_dir = os.path.join(base, sub); os.makedirs(dst_dir, exist_ok=True)
    for f in sorted(os.listdir(src_dir)):
        if not f.endswith(".md"): continue
        body = open(os.path.join(src_dir, f), encoding="utf-8").read()
        url = (re.search(r'^- URL:\s*(\S+)', body, re.M) or [None,""])[1] \
              if re.search(r'^- URL:\s*(\S+)', body, re.M) else ""
        sha = hashlib.sha256(body.encode()).hexdigest()
        dst = os.path.join(dst_dir, f)
        if existing_sha(dst) == sha: continue   # 동일 → 스킵
        fm = f"---\nsource_url: {url}\ningested: {ingested}\nsha256: {sha}\n---\n\n"
        open(dst, "w", encoding="utf-8").write(fm + body)
```
- URL 없는 파일(iOS 저장본, 일부 책)은 빈 `source_url:`로 둔다(정상).

## 2. 파일럿 (전체 컴파일 전 필수)
한 주제(밀도 높은 것, 예: 습관/복리)만 골라 import→concept 합성까지 끝낸 뒤
사용자에게 형식·클러스터 묶음을 확인받는다. OK면 전체로 확장.

## 3. 클러스터링 (메타데이터만 추출)
본문 전체를 컨텍스트에 올리지 말고 Title+Summary만 뽑아 규칙 기반 분류 → `/tmp/cl/<cluster>.txt`로 저장.
한 클러스터가 너무 크면(예: 잡탕 mindset 95개) 2차 세부 분류로 재분할. 균형 목표 대략 5~56개/클러스터.

```python
# 각 raw에서 Title/Summary 추출
ti = re.search(r'^- Full Title:\s*(.+)$', tx, re.M)
su = re.search(r'^- Summary:\s*\n?(.+?)(?=\n- URL:|\n## Highlights|\n- Category)', tx, re.S|re.M)
# 키워드 정규식으로 cluster 배정 → clusters[cluster].append(filename)
# /tmp/cl/<cluster>.txt 에 파일명 한 줄씩 저장
```

## 4. 대량 Compile — subagent 병렬 (동시 3개)
`delegate_task(tasks=[...])`로 클러스터를 큰 것부터 3개씩. 각 task에 다음을 context로 박는다:
- 입력: `/tmp/cl/<cluster>.txt`(파일 목록) + raw 절대경로 prefix
- raw 구조 설명 + **raw 불변**(수정 금지)
- 출력: `<vault>/hermes/concepts/<제목>.md`, 파일명 규칙(한글 자연어/하이픈, 특수문자→-)
- 작업: 의미 주제로 클러스터링, 주제당 page 1개(잘게 쪼개지 말 것; 2+ 소스 같은 주제면 묶기), 단일·비핵심은 통합
- 페이지 형식(반드시): SCHEMA frontmatter, 태그 taxonomy 한정, 첫 줄 요약→핵심 명제 불릿→소스별 `출처: [제목](URL)` + 하이라이트 blockquote, `[[wikilinks]]` 2+(배치 내 상호링크 + 기존 페이지로), 3+ 소스 종합 문단 끝 `^[raw/articles/파일.md]`, 끝에 `---`+`## History`
- **index.md/log.md는 건드리지 말 것**(부모가 통합), `toolsets=['file']`
- 보고: 생성 페이지 파일명 + 묶은 소스 수 + 한 줄 설명 + index 항목 문자열

배치1 완료 후 품질 확인 → 배치2(다음 3 클러스터) → … 순차. 부모가 각 배치 결과를 받아
index.md(Total/Last updated)·log.md(`## [날짜] ingest | ...`)를 한 번에 통합한다.

## 5. 배치마다 직접 검증 (자기보고 불신)
subagent 보고는 self-report라 신뢰 금지 — 배치 끝날 때마다 부모가 `execute_code`로 실측한다:
- 생성 페이지 형식(frontmatter/sources/`[[wikilink]]` 2+/`## History`) 일괄 스캔.
- 깨진 wikilink: **대소문자 불일치 주의**. 이 세션에서 기존 페이지가 `[[LLM-distillation-into-rules]]`로
  대문자 링크했는데 실제 파일은 `llm-...`이라 데드링크였다(Obsidian은 보통 대소문자 무시하지만 lint·정합성엔 잡힌다).
- **배치 간 orphan**: 각 subagent는 자기 배치 안에서만 상호링크하므로, 배치 경계를 넘는 cross-link이 없어
  인바운드 0(고아) 페이지가 다수 생긴다(이 세션 13개). 부모가 마지막에 관련 허브 페이지의
  `## 관련 개념 (추가 연결)` 섹션에 `- [[고아slug]]`를 넣어 인바운드를 만들어준다(History 블록 앞에 삽입).

## 6. index.md는 전면 재생성 (append 아님)
배치마다 index에 줄을 덧붙이면 순서·중복이 엉킨다. 전체 컴파일 끝나면 모든 concept의
`title` + 첫 본문 문단(요약)을 추출해 **주제 그룹별로 묶어 index.md를 통째로 다시 쓴다**.
header의 `Total pages`/`Last updated`도 이때 한 번에 갱신. log.md엔 통합 ingest 항목 1개.

## 7. 정리 후 lint
전체 컴파일 끝나면 7.3 lint로 깨진 wikilink/orphan/index 누락/태그 위반 점검(0 나와야 완료).

## 핵심 교훈
- 200+개를 한 턴에 직접 컴파일 X → 클러스터 분할 + subagent 병렬.
- import(기계적)와 compile(판단) 분리. import는 언제든 안전·재실행 가능, compile만 신중히.
- 원본 export 폴더는 절대 보존. raw도 불변. 모든 합성은 concepts/에서.
