# dotfiles — agent context

Mac 설정과 AI-agent 환경을 재현하는 개인 dotfiles. public(이 repo)이 공통 뼈대이고,
`private/` submodule(사외 머신 전용)이 개인 인프라를 담는다. 사내 fork는 이 repo를
rebase 베이스로 쓰며 private을 초기화하지 않는다.

## 파일 배치 기준 — 새 파일을 추가·백업할 때 순서대로 판정한다

**Q1. secret / 타인 개인정보 / 머신 로컬 상태인가? → git 밖 (양쪽 repo 모두 커밋 금지)**
- secret(토큰·키·auth·.env): Bitwarden(bws)·`~/.hermes/.env` 등으로 주입하고,
  백업에는 `${ENV_VAR}` 플레이스홀더만 남긴다.
- 타인 PII(예: 멘티 roster): gitignore로 제외하고 live·워킹트리에만 둔다.
- 머신 로컬 상태(state.db·세션·로그·캐시·개인 경로 config): gitignore.

**Q2. 사외(개인) 머신에만 존재하거나, 공개되면 개인 인프라·일상 구조가 드러나는가?
→ `private/`** — Hermes·Grok 등 개인 에이전트, services/launchd(포트·Tailscale),
PKM 파이프라인, 개인 거버넌스 문서(INVENTORY·스펙·플랜), 개인 머신 운영 스크립트.

**Q3. 나머지 — 사내 fork가 rebase 베이스로 받아 써야 하는 범용 설정 → public.**
public 판정의 리트머스는 "노출 무해"가 아니라 "사내 fork가 베이스로 필요로 하는가"다.
개인 도구의 백업·복구·E2E와 그 테스트·문서는 stdlib만 쓰거나 범용적인 코드여도 Q2다.
검토된 sanitized 개인 snapshot/intake inventory manifest는 private에 둘 수 있다.
raw credential·타인 PII는 Q1로 private에도 넣지 않는다. 일회성 실행·복구 manifest,
recovery journal·실행 보고서·로그 등 머신 로컬 산출물은 git 밖에 둔다.
재사용할 개인 설계·plan 문서는 private에 둔다. 특정 임시 경로·일회성 checkout·hash에
묶인 통합 실행 계획은 머신 로컬 작업 산출물이므로 git 밖에 둔다.

구체적인 경계 예: `ghostty/config`의 공통 UI 설정, `codex/plugins.toml`과
`claude/skills/make-pr/config.yaml`의 범용 기본값, 공용 Herdr hooks는 public이다.
앱이 만든 template 주석의 머신 절대경로는 중립적인 설명으로 바꾼다. 이 주석 때문에
도구 전체를 private으로 이동하지 않는다. 개인 프로필·인프라 inventory는 private이다.

## 관리 방식 (배치와 직교하는 축)

- **symlink**: 사람이 편집하는 정적 파일. public `link.sh` → `private/link.sh` 위임 순으로
  건다. 홈 쪽 목적지 경로는 계약이므로 임의로 바꾸지 않는다(Hermes cron이 절대경로 의존).
- **copy 백업**: 앱이 atomic write로 재작성하는 파일(Hermes config·cron·profiles,
  Karabiner, herdr 훅 스크립트). symlink 금지 — 링크가 파괴된다.
- 배치를 정한 다음 관리 방식을 별도로 정한다. copy 대상은 비교·sanitization 후 repo에
  regular file로 보관하고 symlink 생성 절차나 `link.sh` 매핑에 넣지 않는다.

## 선택적 개인 확장

개인 checkout이 제공하면 `private/docs/DOTFILES-SYNC.md`를 읽어 개인 자산의 수집·검증
계약을 따른다. 없으면 public만 작업하며 private을 생성하거나 초기화하지 않는다.
public의 범용 sync·보안 검수 계약은 개인 확장 없이 동작해야 한다.

## 작업 규약

- 승인된 경로만 수정하고 기존 미커밋 변경을 보존한다. sync·검증 요청을 live restore·link,
  stage·commit·push 승인으로 확대하지 않는다. commit은 명시적으로 요청된 경우에만 한다.
- 새 백업·편입 커밋 전에 승인된 경로를 stage한 뒤 결정론 검수를 돌린다:
  `python3 claude/skills/dotfiles-sync/scripts/precommit_scan.py <repo>` — exit 0만 통과,
  1은 BLOCK, 2는 검사 실패다. 빈 staged diff는 검증 통과 근거가 아니다.
  secret·타인 PII·public 배치·linker 계약을 검사하며, 승인된 변경 외 stage는 금지다.
  no-stage 검증에서는 별도 임시 index/objects와 명시적 경로를 쓰거나 이 게이트를 미실행으로
  보고한다. 어떤 index에서도 광범위한 `git add -A`를 사용하지 않는다.
- routine은 변경에 맞는 fixture 검증을 하고, 대량 편입·이동·복구/linker·secret 경계 변경은
  실제 전달할 checkout과 변경 파일 hash를 고정해 독립 검토한다. 명시한 검토자·모델을
  따르며 일상 변경에 특정 고비용 모델을 강제하지 않는다. blocker 수정 후 재검증·재검토한다.
  자세한 절차는 `claude/skills/dotfiles-sync/SKILL.md`를 따른다.
- 검증은 임시 fixture에서 수행하고 skip·누락 의존성·빈 필수 suite를 pass로 보고하지 않는다.
  Herdr 사용 시 별도 테스트 pane에서 focus를 보존하고 작업 중 만든 완료 pane만 닫는다.
- 커밋은 `[scope] message`(영어) 컨벤션. 어떤 스크립트·에이전트도 자동 push하지 않는다 —
  push는 커밋 요약을 보여주고 사용자 확인 후에만.
- push 순서: private 먼저, public 나중 (public gitlink가 private 커밋 SHA를 참조).
- vault 등 외부 산출물에는 rm 대신 mv를 쓰고, 판정 기준 없는 단계 진입을 피한다.
