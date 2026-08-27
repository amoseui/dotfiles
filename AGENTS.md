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

## 관리 방식 (배치와 직교하는 축)

- **symlink**: 사람이 편집하는 정적 파일. public `link.sh` → `private/link.sh` 위임 순으로
  건다. 홈 쪽 목적지 경로는 계약이므로 임의로 바꾸지 않는다(Hermes cron이 절대경로 의존).
- **copy 백업**: 앱이 atomic write로 재작성하는 파일(Hermes config·cron·profiles,
  Karabiner, herdr 훅 스크립트). symlink 금지 — 링크가 파괴된다.

## 작업 규약

- 새 백업·편입 커밋 전에 결정론 검수를 돌린다(2026-08-24 Todoist 토큰 사건 재발 방지):
  `python3 claude/skills/dotfiles-sync/scripts/precommit_scan.py <repo>` — exit 1(BLOCK)이면
  커밋 금지. secret(대소문자 무시)·roster형 타인 PII·public 배치 위반·link.sh 파서 사각을
  잡는다. 대량 편입·구조 변경의 push 전에는 `/codex:adversarial-review` 2차 리뷰를 권한다.
- 커밋은 `[scope] message`(영어) 컨벤션. 어떤 스크립트·에이전트도 자동 push하지 않는다 —
  push는 커밋 요약을 보여주고 사용자 확인 후에만.
- push 순서: private 먼저, public 나중 (public gitlink가 private 커밋 SHA를 참조).
- vault 등 외부 산출물에는 rm 대신 mv를 쓰고, 판정 기준 없는 단계 진입을 피한다.
