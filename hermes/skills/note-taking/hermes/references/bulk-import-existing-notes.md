# 기존 노트 대량(100+) → llm-wiki 컴파일 (cluster + subagent fan-out)

Readwise/Bear 익스포트 등 **이미 vault에 있는 수백 개 노트**를 위키로 정리할 때의 절차.
llm-wiki SKILL의 "Bulk Ingest"는 단일 에이전트·소량 가정이라 100+ 규모엔 부족하다 — 이 레시피로 보강한다.

## 0. 가장 먼저: 복사 ≠ 컴파일임을 사용자와 합의

사용자가 "기존 노트를 hermes로 다 복사해서 정리"를 요청해도 그건 llm-wiki 플로우가 **아니다**.
- **복사**: 파일 더미. 교차참조·모순정리·종합이 없음 → 위키 가치 0.
- **컴파일**: raw를 읽어 *주제별로 새로 종합한* concept 페이지 생성.
- 기존 노트의 성격을 먼저 분류: ① 외부 소스 클리핑/하이라이트(Readwise 등) → `raw/`로 흡수 후 컴파일. ② 잡다 메모 → `notes/`로 단순 이동. ③ 이미 정리된 지식 → 소스로 삼아 재종합.
- Readwise 익스포트는 `## Metadata`(Author/Full Title/Category/Summary/URL) + `## Highlights` 구조 → 명백히 **레이어1(raw source)**. "내가 정리한 지식"처럼 보여도 실제론 외부 글의 발췌다.

## 1단계: raw 흡수 (기계적, 안전, execute_code 한 번)

원본 폴더는 **보존**(읽기만), `hermes/raw/articles|books/`로 복사 + raw frontmatter 부착.

```python
import hashlib, re, os
src_dir = "<원본 폴더>"; raw_dir = "<vault>/hermes/raw/articles"; os.makedirs(raw_dir, exist_ok=True)
for f in sorted(os.listdir(src_dir)):
    if not f.endswith(".md"): continue
    with open(os.path.join(src_dir,f),encoding="utf-8") as fh: body=fh.read()
    m=re.search(r'^- URL:\s*(\S+)',body,re.M); url=m.group(1) if m else ""
    sha=hashlib.sha256(body.encode()).hexdigest()
    dst=os.path.join(raw_dir,f)
    # 재실행 안전: 기존 sha256과 같으면 스킵(드리프트면 갱신)
    old=None
    if os.path.exists(dst):
        head=open(dst,encoding="utf-8").read(600)
        mm=re.search(r'^sha256:\s*([0-9a-f]+)',head,re.M); old=mm.group(1) if mm else None
    if old==sha: continue
    open(dst,"w",encoding="utf-8").write(f"---\nsource_url: {url}\ningested: <YYYY-MM-DD>\nsha256: {sha}\n---\n\n"+body)
```

**함정**: `hermes_tools`의 `read_file()` 래퍼는 dict에 `"content"` 키가 **없을 수 있다**(KeyError). execute_code 안에서 raw를 다룰 땐 표준 `open()`을 써라. URL 없는 노트(iOS 저장본/책 메모)는 빈 url로 정상 흡수.

## 2단계: 클러스터링 (컨텍스트 절약 — 메타데이터만)

222개 본문을 컨텍스트에 올리지 말고 제목+Summary만 뽑아 정규식 규칙으로 주제 분류.
- 한 클러스터가 과대(예: mindset 95개)면 **subagent에 못 넘긴다** → 의미별로 재분할(회고/학습/의사결정/창의성/기술 등으로 쪼개 다른 클러스터에 합류).
- 목표 클러스터 크기: 한 subagent당 8~56개. 각 클러스터 파일 목록을 `/tmp/cl/<name>.txt`로 떨궈 subagent가 읽게 한다.

## 3단계: subagent fan-out (동시 3개씩 배치)

`delegate_task` 배치 모드, 큰 클러스터부터. 각 subagent에 **전체 형식 규칙을 context로 박는다**(subagent는 SCHEMA를 모름):
- toolsets=["file"]만 부여(raw 읽기 + write_file).
- 지침에 반드시 포함: raw 경로, frontmatter 형식, **tag taxonomy 전체 목록**(밖 태그 금지), blockquote(>)로 하이라이트 강조 + `출처:[제목](URL)` 명시, `[[wikilinks]]` 최소 2개, 3+소스 종합 문단 `^[raw/...]`, History 블록, **"index.md/log.md는 건드리지 말 것"**(부모가 통합), **"존재하지 않는 페이지 가리키는 wikilink 금지(데드링크)"**.
- 기존 페이지 슬러그를 cross-link 후보로 알려준다(배치가 진행될수록 늘어남).
- 중복 위험: 한 클러스터가 기존 페이지와 겹치면(예: habit의 복리효과·Atomic Habits가 이미 `습관-복리-시스템`에 있음) "이미 처리됨 → 제외하고 cross-link만" 명시.

## 4단계: 배치마다 검증 (subagent 자기보고 불신)

각 배치 후 execute_code로 직접 스캔:
```python
# concepts/ 전수: frontmatter 시작? wikilink>=2? ## History 있음? sources 있음? 깨진 [[link]]?
```
깨진 wikilink = 슬러그(파일명-.md)에 없는 타깃. **대소문자 불일치**(`LLM-...` vs `llm-...`)가 흔한 데드링크 원인.

## 5단계: 최종 통합 (부모만)

모든 배치 후 한 번에: index.md 전 페이지 등록 + Total 갱신, log.md ingest 기록 1건, 기존 페이지 깨진 링크/History 누락 보강, lint(고아·깨진 링크·taxonomy 밖 태그).

## 규모 감각 (이 세션 실측)
222 소스 → 약 60 concept 페이지. 배치당 3 subagent, 배치 3~4회. 각 subagent 2~8분.
