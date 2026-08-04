---
name: rss-triage-ingest
description: |
  Hermes feed pipeline으로 RSS/Gmail/Reader backlog를 수집해 Obsidian
  체크박스 review 노트를 만드는 스킬. APPLY 전에는 외부 상태와 위키를
  변경하지 않는다.
version: 1.0.0
author: Hermes Agent + Amos
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [rss, gmail, reader, triage, obsidian, review]
    category: note-taking
---

# RSS / backlog triage ingest

feed pipeline의 수집 단계만 담당한다. 사용자가 review 노트의 체크박스를 선택하고 별도로 처리를 요청하기 전에는 Gmail unread/read, Reader archive, whitelist, 위키 ingest를 변경하지 않는다.

## 설정과 경로

1. 먼저 `~/.hermes/feed-pipeline/config.yaml`을 읽는다.
2. Hermes venv Python(`~/.hermes/hermes-agent/venv/bin/python`)을 사용한다. 시스템 `python3`를 사용하지 않는다.
3. 파이프라인 스크립트는 `~/.hermes/feed-pipeline/scripts/`에 있다.
4. 결과 review 노트는 설정된 vault의 `6-agents/review/`에 생성한다.
5. credential 파일과 `.env`는 읽거나 출력·복사하지 않는다. 인증 실패는 상태만 보고한다.

## 신규 피드 triage

매일 신규 RSS/Gmail을 수집해 `YYYY-MM-DD-new-feed-review.md`를 만든다.

```bash
WORKDIR=$(mktemp -d "${TMPDIR:-/tmp}/hermes-cron.XXXXXX")
trap 'rm -f "$WORKDIR/fp_gmail.json" "$WORKDIR/fp_rss.json" "$WORKDIR/fp_rss_full.json"; rmdir "$WORKDIR"' EXIT
PY=~/.hermes/hermes-agent/venv/bin/python
PIPE=~/.hermes/feed-pipeline/scripts
DATE=$(TZ=Asia/Seoul date +%Y-%m-%d)-new
$PY "$PIPE/rss_new.py" 26 > "$WORKDIR/fp_rss.json"
$PY "$PIPE/gmail_backlog.py" 40 > "$WORKDIR/fp_gmail.json"
cat "$WORKDIR/fp_rss.json" | $PY "$PIPE/fetch_content.py" > "$WORKDIR/fp_rss_full.json"
$PY "$PIPE/make_review_note.py" --gmail "$WORKDIR/fp_gmail.json" --rss "$WORKDIR/fp_rss_full.json" --date "$DATE"
```

## 누적 backlog triage

Gmail과 Reader의 누적 항목을 수집해 `YYYY-MM-DD-feed-review.md`를 만든다.

```bash
WORKDIR=$(mktemp -d "${TMPDIR:-/tmp}/hermes-cron.XXXXXX")
trap 'rm -f "$WORKDIR/fp_gmail.json" "$WORKDIR/fp_reader.json" "$WORKDIR/fp_reader_full.json"; rmdir "$WORKDIR"' EXIT
PY=~/.hermes/hermes-agent/venv/bin/python
PIPE=~/.hermes/feed-pipeline/scripts
DATE=$(TZ=Asia/Seoul date +%Y-%m-%d)
$PY "$PIPE/gmail_backlog.py" 30 > "$WORKDIR/fp_gmail.json"
$PY "$PIPE/reader_backlog.py" 30 > "$WORKDIR/fp_reader.json"
cat "$WORKDIR/fp_reader.json" | $PY "$PIPE/fetch_content.py" > "$WORKDIR/fp_reader_full.json"
$PY "$PIPE/make_review_note.py" --gmail "$WORKDIR/fp_gmail.json" --reader "$WORKDIR/fp_reader_full.json" --date "$DATE"
```

## 결과와 안전성

- review 노트에는 항목별 `NL+`, `NL-`, `KEEP`, `MERGE`, `SKIP`, `READ`와 상단 `APPLY` 체크박스가 있어야 한다.
- 수집 결과가 0건이어도 파이프라인 오류와 backlog 없음은 구분해 보고한다.
- review 노트만 생성하고, 실제 반영은 별도 사용자 요청에서 수행한다.
- 생성·갱신 결과를 한국어로 간결히 보고한다: 경로, 항목 수, 인증/수집 오류, 외부 상태를 변경하지 않았다는 사실.
