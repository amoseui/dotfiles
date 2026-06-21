---
name: review-claudemd
description: 최근 대화 기록을 분석해 글로벌(~/.claude/CLAUDE.md)·로컬(프로젝트) CLAUDE.md의 개선점을 찾는다. 트리거 — "claudemd 리뷰", "CLAUDE.md 개선", "review claudemd", "지침 점검", "CLAUDE.md 점검해줘" 등.
---

# Review CLAUDE.md from conversation history

최근 대화를 분석해 글로벌(`~/.claude/CLAUDE.md`)과 로컬(프로젝트) CLAUDE.md를 모두 개선한다.

## Step 1: 대화 기록 찾기

프로젝트 대화 기록은 `~/.claude/projects/`에 있다. 폴더명은 프로젝트 경로의 슬래시를 `-`로 치환한 형태다.

```bash
PROJECT_PATH=$(pwd | sed 's|/|-|g')
CONVO_DIR=~/.claude/projects/${PROJECT_PATH}
ls -lt "$CONVO_DIR"/*.jsonl 2>/dev/null | head -20
```

## Step 2: 최근 대화 추출

현재 대화를 제외한 최근 15~20개를 임시 디렉터리로 추출한다:

```bash
SCRATCH=/tmp/claudemd-review-$(date +%s)
mkdir -p "$SCRATCH"

for f in $(ls -t "$CONVO_DIR"/*.jsonl 2>/dev/null | head -20); do
  base=$(basename "$f" .jsonl)
  cat "$f" | jq -r '
    if .type == "user" then
      "USER: " + (if (.message.content|type)=="string" then .message.content else ((.message.content // []) | map(select(.type=="text") | .text) | join("\n")) end)
    elif .type == "assistant" then
      "ASSISTANT: " + ((.message.content // []) | map(select(.type == "text") | .text) | join("\n"))
    else empty end
  ' 2>/dev/null | grep -v "^ASSISTANT: $" > "$SCRATCH/${base}.txt"
done

ls -lhS "$SCRATCH"
```

## Step 3: Sonnet 서브에이전트 병렬 분석

병렬 Sonnet 서브에이전트로 대화를 분석한다. 각 에이전트는 다음을 읽는다:
- 글로벌 CLAUDE.md: `~/.claude/CLAUDE.md`
- 로컬 CLAUDE.md: `./CLAUDE.md` (있으면)
- 대화 파일 묶음

각 에이전트 프롬프트 템플릿:

```
다음을 읽어라:
1. 글로벌 CLAUDE.md: ~/.claude/CLAUDE.md
2. 로컬 CLAUDE.md: [project]/CLAUDE.md
3. 대화: [파일 목록]

두 CLAUDE.md에 비추어 대화를 분석해 다음을 찾아라:
1. 존재하지만 지켜지지 않은 지침 (강화·재서술 필요)
2. 로컬 CLAUDE.md에 추가하면 좋을 패턴 (프로젝트 특화)
3. 글로벌 CLAUDE.md에 추가하면 좋을 패턴 (어디서나 적용)
4. 두 파일 중 오래됐거나 불필요해 보이는 항목

구체적으로. 불릿 포인트만 출력.
```

대화를 크기별로 배치:
- 큰 것(>100KB): 에이전트당 1~2개
- 중간(10~100KB): 에이전트당 3~5개
- 작은 것(<10KB): 에이전트당 5~10개

## Step 4: 결과 집계

모든 에이전트 결과를 다음 섹션으로 종합한다:

1. **지켜지지 않은 지침** — 기존 규칙인데 안 지켜진 것 (더 강한 표현 필요)
2. **추가 제안 - 로컬** — 프로젝트 특화 패턴
3. **추가 제안 - 글로벌** — 어디서나 적용되는 패턴
4. **오래된 항목** — 더 이상 유효하지 않을 수 있는 것

표나 불릿으로 제시하고, 편집 초안을 만들지 사용자에게 물어본다.

> 참고: 내 `~/.claude/CLAUDE.md`는 dotfiles repo(`claude/CLAUDE.md`)로 심링크돼 있으므로, 편집을 적용하면 repo에 반영된다. 적용 후 `[[dotfiles-sync]]`로 동기화한다.
