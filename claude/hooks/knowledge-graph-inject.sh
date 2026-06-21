#!/usr/bin/env bash
# SessionStart 훅: 지식 그래프에서 현재 프로젝트 관련 지식을 컨텍스트에 주입
# KNOWLEDGE_GRAPH_PATH 환경변수가 설정되어 있고, 매칭되는 프로젝트가 있을 때만 동작

set -euo pipefail

# 디버그 로그
DEBUG_LOG="/tmp/knowledge-graph-inject.log"
debug() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$DEBUG_LOG"; }
debug "=== SessionStart 훅 시작 ==="

# 환경변수 체크
KG_PATH="${KNOWLEDGE_GRAPH_PATH:-}"
debug "KG_PATH=$KG_PATH"
if [[ -z "$KG_PATH" ]]; then
  debug "KG_PATH 비어있음, 종료"
  exit 0
fi

# ~ 확장
KG_PATH="${KG_PATH/#\~/$HOME}"

# INDEX.md 존재 확인
if [[ ! -f "$KG_PATH/INDEX.md" ]]; then
  exit 0
fi

# stdin에서 hook 입력 읽기 (타임아웃 방지: stdin이 없을 수 있음)
HOOK_INPUT=""
if read -t 1 -r FIRST_LINE; then
  HOOK_INPUT="$FIRST_LINE"
  while read -t 0.1 -r LINE; do
    HOOK_INPUT+="$LINE"
  done
fi
debug "HOOK_INPUT=$HOOK_INPUT"

# CWD 추출: stdin JSON → CLAUDE_PROJECT_DIR → PWD 순으로 폴백
CWD=""
if [[ -n "$HOOK_INPUT" ]]; then
  CWD=$(echo "$HOOK_INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('cwd',''))" 2>/dev/null || echo "")
fi
if [[ -z "$CWD" ]]; then
  CWD="${CLAUDE_PROJECT_DIR:-${PWD:-}}"
fi
debug "CWD=$CWD"
if [[ -z "$CWD" ]]; then
  debug "CWD 비어있음, 종료"
  exit 0
fi

# 프로젝트 식별: git remote URL 우선, 디렉토리명 폴백
PROJECT_NAME=""
if GIT_URL=$(git -C "$CWD" remote get-url origin 2>/dev/null); then
  PROJECT_NAME=$(basename "$GIT_URL" .git)
fi
if [[ -z "$PROJECT_NAME" ]]; then
  PROJECT_NAME=$(basename "$CWD")
fi

# 프로젝트 인덱스 경로
PROJECT_INDEX="$KG_PATH/projects/$PROJECT_NAME/_index.md"

# 출력 구성
OUTPUT=""

if [[ -f "$PROJECT_INDEX" ]]; then
  OUTPUT+="[Knowledge Graph] 프로젝트: $PROJECT_NAME"$'\n\n'
  OUTPUT+="## 프로젝트 지식 ($PROJECT_NAME)"$'\n'
  OUTPUT+=$(sed -n '/^## 지식 목록/,$ p' "$PROJECT_INDEX" | tail -n +2)
  OUTPUT+=$'\n\n'
fi

# common 지식 주입 (INDEX.md의 ## Common ~ ## Projects 사이)
COMMON_SECTION=$(sed -n '/^## Common/,/^## /{ /^## Projects/d; /^## Common/d; p; }' "$KG_PATH/INDEX.md")
if [[ -n "$COMMON_SECTION" ]]; then
  if [[ -z "$OUTPUT" ]]; then
    OUTPUT+="[Knowledge Graph]"$'\n\n'
  fi
  OUTPUT+="## 공통 지식"$'\n'
  OUTPUT+="$COMMON_SECTION"$'\n'
fi

# 내용이 있으면 stdout으로 출력
if [[ -n "$OUTPUT" ]]; then
  debug "출력 생성 성공, 길이=${#OUTPUT}"
  echo "$OUTPUT"
else
  debug "출력할 내용 없음"
fi
debug "=== SessionStart 훅 종료 ==="
