---
name: workspace-flow
description: |
  대규모·다단계 작업을 brainstorm → plan → execute → review → ship 순서로 일관되게
  진행하는 얇은 오케스트레이터. 기존 superpowers 스킬 + Workflow 도구 + Codex 리뷰를
  정해진 순서로 위임·조율한다. 각 단계 경계에서 사용자 승인을 받는다.
  트리거: "workspace flow", "workspace workflow", "워크스페이스 플로우로 해줘",
  "이 작업 정식 절차로 진행", "/workspace-flow" 등. 대규모 리뉴얼·기능 구현 요청 시.
argument-hint: "[작업 목표]"
---

# Workspace Flow

대규모·다단계 작업을 **brainstorm → plan → execute → review → ship** 5단계로 진행하는
얇은 오케스트레이터다. 자체 로직은 최소화하고, 기존 superpowers 스킬 · Workflow 도구 ·
Codex 리뷰를 정해진 순서로 위임한다.

## 원칙

- **Interactive by default**: 각 단계 경계에서 사용자 승인을 받고 다음으로 넘어간다.
- 이상 상황(테스트 실패·예상치 못한 파일 상태·권한 오류)은 멈추고 상황 + 선택지를 보고한다.
- spec/plan은 `docs/superpowers/`에 두고 대상 repo에서 gitignore한다.
- 범위 밖: Scale Gate, 세션 로깅, advisor 매트릭스, 훅 경계(필요해지면 후속 확장).

## 0단계: 사전 점검

- 대상 repo의 `.gitignore`에 `docs/superpowers/` 규칙이 없으면 추가한다(spec/plan을 로컬에만 보관).
- 작업 목표가 인자로 주어졌으면 1단계 brainstorming에 전달한다.

## 1단계: Brainstorm

- `superpowers:brainstorming` 스킬을 호출한다.
- 산출물 spec은 `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`.
- **게이트**: 사용자가 spec을 승인해야 2단계로 넘어간다.

## 2단계: Plan

- `superpowers:writing-plans` 스킬을 호출한다.
- 산출물 plan은 `docs/superpowers/plans/YYYY-MM-DD-<feature>.md`.
- **게이트**: 사용자가 plan을 승인해야 3단계로 넘어간다.

## 3단계: Execute

- 계획 태스크를 **Workflow 도구로 순차 실행**한다(공유 파일 충돌 방지).
- 각 태스크: 실패 테스트 → 구현 → 통과 → build/test 검증 → commit (TDD).
- 어떤 태스크가 검증에 실패하면 그 위에 다음 태스크를 쌓지 않고 **중단·보고**한다.
- 막힌 작업은 `superpowers:systematic-debugging` 우선. 그래도 안 풀리면
  `codex:codex-rescue` 서브에이전트(write 가능)로 위임할 수 있다(선택).
- **게이트**: 실행 시작 전 사용자에게 확인한다.

## 4단계: Review

먼저 Claude 리뷰, 그다음 Codex 리뷰 순서로 진행한다.

1. `superpowers:requesting-code-review`로 스펙·스타일·결함·머지 준비를 커버한다.
2. Codex가 놓치기 쉬운 영역(SECURITY / HIDDEN_ASSUMPTION / ARCHITECTURE / BLIND_SPOT)을
   집중 검토한다. **SlashCommand 도구로** 다음을 호출한다(bash 미사용):
   - `/codex:review` — 결함 중심 리뷰
   - `/codex:adversarial-review` — 설계·가정 challenge 리뷰
3. 재리뷰는 체크포인트당 1회. 이슈가 반복되면 사용자에게 에스컬레이션한다.

### Codex 호출 전제 — 플래그 확인 + 폴백

`/codex:review`·`/codex:adversarial-review`는 플러그인이 `disable-model-invocation: true`로
두어 기본적으로 모델이 호출할 수 없다. 이 스킬은 두 커맨드 파일의 플래그를 false로 패치해 둔다.
Review 단계 진입 시 플래그 상태를 **Read로 확인**한다:

- `false`로 패치돼 있으면 → SlashCommand로 자동 호출.
- `true`로 원복돼 있으면(플러그인 업데이트/reload로 캐시 덮어쓰기) → 사용자에게
  "Codex 커맨드 플래그가 원복됐습니다. 재패치할까요?"라고 묻는다.
  - 동의 → 두 커맨드 파일을 다시 false로 패치 후 호출.
  - 거부 → 그 회차는 사용자가 `/codex:review`·`/codex:adversarial-review`를 직접 실행하도록 요청(수동 폴백).

플러그인 커맨드 경로: `~/.claude/plugins/cache/openai-codex/codex/<ver>/commands/{review,adversarial-review}.md`.

- **게이트**: 리뷰 결과를 triage해 사용자와 합의한다.

## 5단계: Ship

- `superpowers:verification-before-completion`으로 완료 주장 전 검증 명령을 실제 실행·확인한다.
- `superpowers:finishing-a-development-branch`로 merge/PR/cleanup 선택지를 제시한다.
- **PR은 자동 생성하지 않는다.** 사용자가 원하면 `make-pr`를 별도로 호출한다.
- **게이트**: ship 방식(merge/cleanup 등)은 사용자가 결정한다.

## 참고

- 이 스킬은 절차(rigid)다. 단계를 건너뛰지 않되, 사용자가 명시적으로 특정 단계를 생략하라고 하면 따른다.
- 각 단계는 기존 자산에 위임한다. 이 스킬이 직접 구현·리뷰·검증 로직을 재발명하지 않는다.
