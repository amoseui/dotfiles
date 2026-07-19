---
name: monthly-review
description: |
  월간 에이전트 인프라 점검(로드맵 T1-2의 실행체): ① transcript·history 사용
  계측(usage_audit.py) ② INVENTORY.md 소화 판정 갱신 ③ CLAUDE.md 개선점
  리뷰(대화 기록 병렬 분석) ④ dotfiles 심링크 무결성 점검을 한 번에 수행한다.
  트리거: "인프라 점검", "월간 점검", "monthly review", "infra review",
  "스킬 사용 통계", "에이전트 설정 점검", "/monthly-review" 등. 월 1회 권장 —
  INVENTORY.md 하단의 다음 점검 예정일이 지났으면 Claude가 먼저 실행을 제안한다.
---

# monthly-review — 월간 에이전트 인프라 점검

계측 → 판정 → 지침 리뷰 → 링크 점검의 순서로, 이 저장소의 에이전트 설정이
"실사용 데이터"에 근거해 유지·수정·폐기되도록 하는 플라이휠 루틴이다.
(판정 기준의 원천: `docs/superpowers/specs/2026-07-05-agent-infra-roadmap-design.md` §3)

## 0. 전제

- dotfiles repo 경로는 dotfiles-sync와 같은 state 파일에서 읽는다:

```bash
REPO=$(cat "${XDG_STATE_HOME:-$HOME/.local/state}/dotfiles-sync/repo-path" 2>/dev/null)
[ -d "$REPO/.git" ] && echo "REPO=$REPO" || echo "NOT_CONFIGURED"
```

- `NOT_CONFIGURED`면 사용자에게 repo 절대 경로를 한 번 묻고 같은 파일에 저장한다.
- 이 스킬은 읽기 위주다. 파일 쓰기는 INVENTORY.md 갱신(사용자 승인 후)과
  CLAUDE.md 편집(사용자 승인 후)뿐이다.

## 1. 사용 계측

```bash
python3 ~/.claude/skills/monthly-review/scripts/usage_audit.py
```

- 집계 항목: Skill 도구 호출(스킬별·최근 사용일), 슬래시 커맨드(transcript
  `<command-name>` + history.jsonl), 자연어 키워드 트리거, 서브에이전트 사용,
  프로젝트별 세션·프롬프트 수, 월별 추이.
- **한계를 함께 보고한다**: transcript는 주기 cleanup으로 최근 분량만 남는다.
  `.last-cleanup` 시각과 잔존 프로젝트 수를 결과에 명시한다.

## 2. INVENTORY 소화 판정 갱신

`$REPO/docs/INVENTORY.md`를 읽고, 계측 결과로 각 구성요소를 재판정한다.

| 판정 | 기준 |
|------|------|
| 유지·승격 | 최근 2주 내 3회 이상 실사용, 또는 다른 구성요소가 의존 |
| 수정·재설계 | 쓰긴 쓰는데 매번 거슬림 → 내 맥락에 맞게 고침 |
| 보류 | 사용 0회지만 유지비용도 0 → 다음 리뷰로 이월 |
| 폐기 | 4주 무사용 + 유지비용 있음 |

- 판정 변경안(무엇을 왜 바꾸는지 계측 수치와 함께)을 표로 제시하고
  **사용자 승인 후에만** INVENTORY.md를 갱신한다. 근거·메모 열에 수치를 남긴다.
- 무사용 스킬은 폐기 전에 "왜 안 쓰는지"(중복? 잊음? 불편?)를 사용자에게
  한 번 확인한다 — 원인이 '잊음'이면 폐기 대신 트리거·루틴 편입을 검토한다.
- 갱신일과 다음 점검 예정일(+1개월)을 INVENTORY.md 하단에 기록한다.

## 3. CLAUDE.md 리뷰 (대화 기록 분석)

최근 대화에서 글로벌(`~/.claude/CLAUDE.md`)·로컬(프로젝트) CLAUDE.md의
개선점을 찾는다.

1. 대화 추출 — 최근 자주 쓴 프로젝트 2~3개(계측 1의 프로젝트 상위)에서
   현재 대화를 제외한 최근 대화 15~20개를 임시 디렉터리로 추출한다:

```bash
SCRATCH=$(mktemp -d /tmp/monthly-review.XXXXXX)
for CONVO_DIR in ~/.claude/projects/<상위 프로젝트 디렉터리들>; do
  for f in $(ls -t "$CONVO_DIR"/*.jsonl 2>/dev/null | head -10); do
    base=$(basename "$f" .jsonl)
    jq -r '
      if .type == "user" then
        "USER: " + (if (.message.content|type)=="string" then .message.content
          else ((.message.content // []) | map(select(.type=="text") | .text) | join("\n")) end)
      elif .type == "assistant" then
        "ASSISTANT: " + ((.message.content // []) | map(select(.type == "text") | .text) | join("\n"))
      else empty end' "$f" 2>/dev/null | grep -v "^ASSISTANT: $" > "$SCRATCH/${base}.txt"
  done
done
ls -lhS "$SCRATCH"
```

2. 병렬 Sonnet 서브에이전트 분석 — 대화를 크기별 배치(큰 것 1~2개/중간
   3~5개/작은 것 5~10개)로 나눠 각 에이전트에 전달. 프롬프트 템플릿:

```
다음을 읽어라:
1. 글로벌 CLAUDE.md: ~/.claude/CLAUDE.md
2. 로컬 CLAUDE.md: <project>/CLAUDE.md (있으면)
3. 대화: <파일 목록>

두 CLAUDE.md에 비추어 대화를 분석해 다음을 찾아라:
1. 존재하지만 지켜지지 않은 지침 (강화·재서술 필요)
2. 로컬 CLAUDE.md에 추가하면 좋을 패턴 (프로젝트 특화)
3. 글로벌 CLAUDE.md에 추가하면 좋을 패턴 (어디서나 적용)
4. 두 파일 중 오래됐거나 불필요해 보이는 항목

구체적으로. 불릿 포인트만 출력.
```

3. 집계 — ① 지켜지지 않은 지침 ② 추가 제안(로컬) ③ 추가 제안(글로벌)
   ④ 오래된 항목 4개 섹션으로 종합해 제시하고, 편집을 원하는지 물어본다.
   글로벌 CLAUDE.md는 repo 심링크이므로 편집하면 곧 repo 변경이다 — 적용 후
   `[[dotfiles-sync]]`로 커밋한다. 끝나면 `rm -rf "$SCRATCH"`.

## 4. 심링크 무결성 점검

link.sh 선언과 실제 홈 디렉터리 상태를 대조한다(settings.json 심링크 파괴
같은 drift의 조기 발견 — 2026-07-18 orca 사례 참고):

```bash
DOTFILES_PATH="$REPO"
# link_file 단건 매핑 검사
grep -E '^link_file ' "$REPO/link.sh" | while read -r _ src dst; do
  src=$(eval echo "$src"); dst=$(eval echo "$dst")
  if   [ -L "$dst" ] && [ "$(readlink "$dst")" = "$src" ]; then echo "OK           $dst"
  elif [ -L "$dst" ]; then echo "WRONG_TARGET $dst -> $(readlink "$dst")"
  elif [ -e "$dst" ]; then echo "NOT_SYMLINK  $dst"
  else                     echo "MISSING      $dst"
  fi
done
# link_dir_contents 매핑(agents/commands/skills)은 항목별 검사
for pair in "claude/agents:$HOME/.claude/agents" "claude/commands:$HOME/.claude/commands" "claude/skills:$HOME/.claude/skills"; do
  srcdir="$REPO/${pair%%:*}"; dstdir="${pair##*:}"
  for entry in "$srcdir"/*; do
    [ -e "$entry" ] || continue
    name=$(basename "$entry"); [ "$name" = ".gitkeep" ] && continue
    dst="$dstdir/$name"
    if   [ -L "$dst" ] && [ "$(readlink "$dst")" = "$entry" ]; then echo "OK           $dst"
    else echo "BROKEN       $dst"
    fi
  done
  # repo에 없는데 심링크가 남은 dangling 항목
  for dst in "$dstdir"/*; do
    [ -L "$dst" ] || continue
    [ -e "$dst" ] || echo "DANGLING     $dst -> $(readlink "$dst")"
  done
done
```

- `OK` 외 항목은 원인(어느 도구가 언제 바꿨는지 mtime 포함)과 복구안을 보고
  한다. 복구는 dotfiles-sync 스킬의 "최초 링크 생성 절차"를 따르고, 실행
  전 사용자 확인을 받는다.

## 5. 보고

- 계측 요약(활발/저조/무사용), INVENTORY 판정 변경, CLAUDE.md 개선안 채택
  내역, 링크 상태를 한 화면으로 보고한다.
- "이번 점검이 답하지 못한 것"(계측 사각 — transcript cleanup 범위,
  Codex 사용 내역 미집계 등)을 함께 적는다.

## 의존성

- `python3` (stdlib only — usage_audit.py)
- `jq` (대화 추출)
- dotfiles repo + `~/.local/state/dotfiles-sync/repo-path`
