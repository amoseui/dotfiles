---
name: pkm-push
description: |
  맥북(또는 보조 머신)에서 작업 종료 시 그날의 Claude Code + Codex 사용 내역을
  결정론적으로 수집해 digest JSON으로 만들고, 동기되는 Obsidian vault의 공유 인박스
  (hermes/inbox/codex-claude/)에 밀어넣는다. 실제 노트 합성·daily 백링크는 이 머신이
  아니라 Hermes가 도는 메인 맥에서 pkm-collect가 수행한다(역할 분리).
  트리거: "pkm push", "작업 내역 밀어줘", "오늘 내역 vault로", "push digest",
  하루 작업을 마치며 이 머신의 AI 사용 내역을 메인 머신으로 보내달라는 요청 시.
---

# pkm-push (보조 머신 → vault 인박스)

이 머신의 오늘 Claude Code/Codex 내역을 **digest JSON**으로 수집해 동기 vault의
공유 인박스에 저장한다. **읽기 전용 수집 + 인박스 쓰기만** 한다(노트 작성·요약은 메인 머신 몫).

## 전제 / 경로

- collect.py 재사용: 같은 dotfiles의 `~/.claude/skills/pkm-collect/scripts/collect.py`
  (Claude `~/.claude/projects` + Codex `~/.codex/sessions`,`~/.codex/history.jsonl`을 함께 수집).
- vault 루트는 머신마다 다를 수 있다 → **`~/.claude/skills/pkm-push/config.yaml`의 `vault_path`에서 읽는다**.
  (이 머신의 vault 경로 한 줄만 맞추면 됨. config가 없으면 사용자에게 묻고 만든다.)
- 인박스: `{vault}/hermes/inbox/codex-claude/`. 파일명 `{hostname}-{YYYY-MM-DD-HHMM}.json`.
- digest는 raw 수집물이다(민감 세션은 collect.py가 이미 제외). 인박스 파일은 메인 머신이
  처리 후 보관/이동하므로 여기서는 덮어쓰지 않고 매번 새 타임스탬프 파일로 남긴다.

## 절차

### 0. config 로드
```bash
cat ~/.claude/skills/pkm-push/config.yaml 2>/dev/null || echo "NO_CONFIG"
```
- 있으면 `vault_path`(+선택 `exclude_keywords`)를 파싱.
- 없으면(NO_CONFIG) `AskUserQuestion`으로 이 머신의 vault 절대경로를 묻고
  `config.example.yaml` 형식으로 `~/.claude/skills/pkm-push/config.yaml`을 Write로 생성한 뒤 진행.

### 1. 수집 (collect.py → digest 파일)
mktemp로 임시 파일을 만들고(zsh noclobber → `>|`) digest를 받아 내용/세션 수를 확인한다:
```bash
VAULT="<config의 vault_path>"
INBOX="$VAULT/hermes/inbox/codex-claude"
mkdir -p "$INBOX"
HOST=$(hostname -s)
STAMP=$(date +%Y-%m-%d-%H%M)
OUT="$INBOX/$HOST-$STAMP.json"

python3 ~/.claude/skills/pkm-collect/scripts/collect.py \
  --vault "$VAULT" \
  --note-dir "hermes/notes" \
  --exclude-keywords "의료,병원,보험,건강검진,진료,대장내시경" >| "$OUT"

# 수집 결과 확인 (세션 수). 0이면 보고만 하고 빈 파일은 지운다.
python3 - "$OUT" <<'PY'
import json,sys,os
p=sys.argv[1]
d=json.load(open(p,encoding="utf-8"))
n=len(d.get("sessions",[]))
print(f"sessions={n} since={d.get('since')} file={p}")
if n==0:
    os.remove(p); print("EMPTY: removed (밀어낼 내역 없음)")
PY
```
- `--since`를 주지 않으면 collect.py가 이 머신의 `pkm-collect/state.json` 마커(없으면 오늘 00:00)부터 수집한다.
- digest 본문(원본 트랜스크립트)은 절대 컨텍스트로 읽지 않는다. 세션 수·메타만 확인.

### 2. (선택) LLM 보강 요약
사용자가 "요약까지" 원하면, digest.sessions의 `user_prompts`/`edited_files`/`project`만 보고
인박스 파일 옆에 `{HOST}-{STAMP}.summary.md`로 **머신·날짜별 한 줄 요약 목록**을 남길 수 있다
(선택). 노트 본체 합성은 메인 머신 pkm-collect가 하므로 여기서는 강요하지 않는다.

### 3. 동기 확인 + 보고
- 파일이 `{vault}/hermes/inbox/codex-claude/`에 생성됐는지 `ls`로 확인.
- vault가 iCloud/Obsidian Sync로 동기되므로, **메인 맥의 Hermes pkm-collect가 다음 실행 때
  이 인박스를 읽어 노트로 합성**한다고 사용자에게 안내.
- 보고: 생성한 파일 경로, 수집 세션 수, since 시각.

## 주의
- **인박스에 쓰는 것 외에 vault를 수정하지 않는다**(노트 생성·daily 편집은 메인 머신 몫).
- 민감(의료/개인) 세션은 collect.py가 digest에서 이미 제외 → 인박스에 안 들어간다.
- 원본 트랜스크립트 전체를 읽지 않는다(토큰 폭발 방지). digest 메타만 본다.
- 같은 날 여러 번 push해도 타임스탬프가 달라 덮어쓰지 않는다. 중복 세션은 메인 머신이 마커/중복판정으로 거른다.

## 의존성
- `python3` (stdlib only) + dotfiles의 `pkm-collect/scripts/collect.py` 및 보조 모듈
- 동기되는 Obsidian vault (iCloud/Obsidian Sync)
- `AskUserQuestion`(최초 config 생성 시)
