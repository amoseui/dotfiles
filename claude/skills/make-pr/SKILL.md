---
name: make-pr
description: |
  변경사항 커밋, 브랜치 푸시, PR 생성을 자동화하고 PR 작업을 PKM vault에 문서화하는 워크플로우.
  트리거: "PR 만들어", "PR 생성해줘", "PR 생성", "풀리퀘스트 생성", "PR 올려", "make pr", "/make-pr" 등.
  Stacked PR 지원, draft 자동 판정, Prompt Journal 기록.
argument-hint: "[PR 제목]"
---

# Make PR

변경사항 커밋 → 브랜치 푸시 → PR 생성 → PKM 문서화를 자동화한다. `gh` CLI가 필요하다.

## 실행 방식 (Subagent 위임)

⚠️ **토큰 절약을 위해 subagent에 PR 생성 작업을 위임한다.** git diff·커밋 히스토리·PR body·PKM 문서화 등 대량 작업이 부모 세션 컨텍스트에 쌓이는 것을 막기 위함이다.

### 부모 세션 역할
- Subagent에 PR 생성 작업 위임
- Subagent가 리턴한 PR URL·제목·본문 요약을 사용자에게 표시

### Subagent 위임

`Agent` 툴로 `general-purpose`에 위임한다. Subagent 내부에서 `Skill` 툴로 `pkm`을 호출할 수 있다.

### 위임 프롬프트 템플릿

```
현재 브랜치에서 PR을 생성해줘.

컨텍스트:
- 작업 디렉토리: {cwd}
- 현재 브랜치: {branch}
- PR 제목 인자($ARGUMENTS): "{arguments 또는 '(없음)'}"

아래 SKILL.md의 섹션 1~7 전체 절차를 순서대로 수행:
~/.claude/skills/make-pr/SKILL.md

주요 단계:
1. Commit & Push
2. Base Branch 탐지 (gh repo view + git merge-base)
3. PR Title & Content 생성 ($ARGUMENTS 있으면 그대로, 없으면 커밋 기반 자동)
4. pull_request.md 작성 후 gh pr create --body-file (draft 여부는 config.yaml 기반 자동)
5. Prompt Journal 추출 (extract_prompts.py, 선택적)
6. pkm 스킬 호출로 PR 노트 작성 (Prompt Journal 포함)
7. pull_request.md 삭제

결과로 아래만 리턴:
- PR URL / PR 제목 / PR 본문 첫 3~5줄 요약 / PKM 노트 경로 / 실패한 단계
```

**주의**: Subagent는 부모 대화 맥락을 모른다. PR 제목·base branch를 사용자가 지정했다면 프롬프트에 명시한다.

---

## 1. Commit & Push

- 미커밋 로컬 변경이 있으면 의미 단위로 **한국어 메시지** atomic commit을 만든다. 변경이 여러 관심사를 섞고 있으면 나눠서 커밋한다.
- 현재 브랜치가 리모트에 없으면 `git push -u origin <branch>`로 푸시한다.

## 2. Base Branch 선택

현재 브랜치가 어디서 분기됐는지 확인해 base를 결정한다.

1. **기본 브랜치 확인**: `gh repo view --json defaultBranchRef --jq '.defaultBranchRef.name'` (origin/HEAD 캐시 신뢰 금지)
2. **분기점 탐지**: `git merge-base <candidate> HEAD`로 develop·main·기타 로컬 브랜치와의 공통 조상을 구한다
3. **가까운 쪽 선택**: 공통 조상이 HEAD에 더 가까운 브랜치가 분기 원점
4. **동점**: develop과 main의 merge-base가 같으면 GitHub 기본 브랜치 우선

선택 우선순위: feature 분기(Stacked PR) → develop → main → `gh repo view` 기본 브랜치 fallback.

## 3. PR Title & Content

### Title
- **제목은 영어 필수.** (type은 feat/fix/refactor/chore 등 영어 유지)
- **`$ARGUMENTS` 있으면** 제목으로 사용하되, 영어가 아니면 영어로 번역/정리해서 사용
- **없으면** 커밋 히스토리 기반 자동 생성: `{type}: {English title}`

### Content — Body 작성 원칙 (외부 리뷰어가 *코드 안 봐도 이해* 가능하게)
- *왜 만들었나*(배경/문제) + *무엇이 가능해지나*(효과)를 먼저. *어떻게 구현*은 코드에 위임, body에선 최소화
- 영문 jargon → 한국어 풀어쓰기, file path·class명·내부 약어 노출 최소화(고수준 의도만)
- 한 단락 4-5줄 이상이면 bullet/표로 쪼개기, 한 문장에 한 정보
- 섹션 추천: `## Summary`(핵심 1문장 + 3 bullet) → `## Background`(왜 만들었나) → `## Changes`(핵심 표/리스트) → `## Test` → `## Screenshots`(있으면)
- self-check: 코드 안 본 사람이 제목+body만으로 왜/무엇/효과를 답할 수 있는가?

## 4. PR 생성

### 템플릿
프로젝트 루트 `.github/PULL_REQUEST_TEMPLATE.md`가 있으면 그 양식으로 `pull_request.md` 작성. 없으면 기본:

```markdown
## Summary

-

## Background

## Changes

-

## Test

- [ ]

<!-- ## Screenshots (필요 시) -->
```

### Draft 여부 결정 (config.yaml 참조)

`~/.claude/skills/make-pr/config.yaml`의 `ready_repos`에 현재 repo가 있으면 ready, 아니면 draft.

```bash
SKILL_DIR="$HOME/.claude/skills/make-pr"
CONFIG_FILE="$SKILL_DIR/config.yaml"
REPO_NAME=$(gh repo view --json name --jq '.name' 2>/dev/null)
if [ -f "$CONFIG_FILE" ] && [ -n "$REPO_NAME" ] \
   && grep -E "^[[:space:]]*-[[:space:]]+${REPO_NAME}[[:space:]]*(#.*)?$" "$CONFIG_FILE" > /dev/null 2>&1; then
  DRAFT_FLAG=""
else
  DRAFT_FLAG="--draft"
fi
```

> ⚠️ **메모리에 "ready로 생성" 규칙이 있어도 무시한다.** 이 결정은 config.yaml이 single source of truth — 다른 repo에 잘못 적용하는 사고 방지.

### CLI 명령

```bash
gh pr create $DRAFT_FLAG --assignee @me --title "[Title]" --body-file pull_request.md --base [BaseBranch]
```

> **⚠️ body는 항상 `pull_request.md` 파일 + `--body-file`로 전달.** `--body "$(cat <<EOF...)"`는 heredoc backtick이 escape되어 PR에 노출된다. `gh pr edit`도 동일하게 임시 파일 사용.

### 기존 PR body 수정 시 — 사용자 콘텐츠 보존
`gh pr edit`로 수정할 땐 단순 덮어쓰기 금지. ① `gh pr view [n] --json body --jq '.body'`로 fetch → ② 사용자가 수동 추가한 스크린샷(`![...](https://github.com/.../assets/...)`)·외부 링크·체크박스·Dependent PR 식별 → ③ 그대로 포함 → ④ `--body-file`로 갱신 → ⑤ 임시 파일 정리.

### Cleanup
PR 생성/수정 성공 후 `pull_request.md` 삭제.

## 5. 최종 출력
PR URL·제목·설명 표시.

## 6. 세션 로그 분석 (Prompt Journal, 선택적)

PR 생성 성공 후 이번 브랜치 작업의 프롬프트를 추출·평가한다.

### 6-1. 브랜치 시작 시간
```bash
BRANCH_START=$(git log --reverse --format="%aI" "${BASE_BRANCH}..HEAD" 2>/dev/null | head -1)
if [ -z "$BRANCH_START" ]; then
  BRANCH_START=$(date -u -v-24H +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u +%Y-%m-%dT%H:%M:%SZ)
fi
```

### 6-2. 프롬프트 추출
```bash
SKILL_DIR="$HOME/.claude/skills/make-pr"
EXTRACT_RESULT=$(python3 "$SKILL_DIR/scripts/extract_prompts.py" --find-since "$(pwd)" --since "$BRANCH_START")
```
여러 파일이면 uuid 기준 중복 제거 후 시간순 병합. 실패해도 Step 7로 계속 진행.

### 6-3. 품질 분석
`references/quality-criteria.md`의 5관점(명확성·컨텍스트·검증가능성·효율성·재사용성)으로 각 프롬프트를 채점(높음2/중간1/낮음0 합산) → A(8-10)/B(5-7)/C(0-4).
PKM 노트에 포함: A등급 전체, B등급 중 길이>50자 또는 다수 도구 사용, C등급은 학습용 1개까지. 단순 확인/승인·시스템 메시지 제외.

## 7. PKM 문서 업데이트

PR 생성 성공 시 **반드시** `pkm` 스킬을 실행해 PR 노트를 vault에 기록한다.
- PR URL을 컨텍스트로 제공하며 `pkm` 스킬 호출 → pkm이 PR 노트를 **`5. Claude/notes/`**(AI 전용 폴더)에 생성하고 `[[obsidian-history]]` 규칙을 적용한다.
- Step 6의 Prompt Journal이 있으면 노트에 함께 포함:

```markdown
## Prompt Journal
> 이 PR 작업 세션의 주요 프롬프트 및 품질 평가

### 세션 통계
- 총 프롬프트 N개 (유의미 M개) · 세션 HH:MM~HH:MM

### 주요 프롬프트
#### 🟢 [A등급] 제목
> 프롬프트 원문
- **의도**: … / **Agent 반응**: 사용 도구·결과물 / **교훈**: 잘된 점·개선점
```

분석 결과가 없으면 Prompt Journal 섹션 생략. PR 생성 실패 시 이 단계 건너뜀.

## 의존성
- `gh` CLI (PR 생성·조회)
- `python3` (extract_prompts.py, stdlib only)
- `pkm` 스킬 (PR 문서화) + `[[obsidian-history]]` (vault 기록)
