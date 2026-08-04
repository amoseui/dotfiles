# Cross-Agent Wiki Handoff Verification Reference

## 검색 체크리스트

1. 활성 PKM 설정에서 `vault_path`, `wiki_dir`, `wiki_schema`, `wiki_index`, `wiki_log`를 읽는다.
2. `SCHEMA.md`, `index.md`, `log.md` 최신 20~30줄을 읽는다.
3. 위키 내용에서 `Claude`, `Codex`, `Hermes`, `Grok`, `인수인계`, `이어받`, `다음 작업`, `현재 상태`, `handoff`, `handover`, `next steps`, `continuation`을 조합해 검색한다.
4. 파일명은 `*인수*`, `*handoff*`, `*handover*`로 별도 검색한다.
5. 후보의 frontmatter, 상태/다음 작업, `## History`, outbound wikilink를 읽는다.
6. `sources:` 원문과 `index.md`·`log.md` 등재를 교차 확인한다.

## Evidence matrix

| 질문 | 근거 | 보고 |
|---|---|---|
| 컴파일된 handoff가 있는가? | 후보 페이지 + frontmatter/History | 확인됨 / 찾지 못함 |
| 의도적으로 ingest됐는가? | `index.md` + `log.md` | 확인됨 / 불완전 |
| 원문이 남아 있는가? | `sources:` 대상 열기 | 검증됨 / 미검증 |
| 전체 인수인계인가? | 상세 운영 정보의 범위 | 전체 / 요약만 |
| 상태가 충돌하는가? | 페이지·원문 날짜/상태 | 최신 상태 + 이전 맥락 |

확인 전용 요청에서는 wiki를 수정하지 않는다. 수정 요청이 있으면 frontmatter·wikilink·index·log·History를 함께 갱신한다.
