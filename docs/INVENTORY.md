# 구성요소 인벤토리 (Component Inventory)

에이전트 인프라 로드맵 T1-1의 산출물이자, 모든 구성요소의 출처·상태·판정을 기록하는 대장.
(로드맵 스펙은 `docs/superpowers/specs/`에 로컬 보관 — gitignore됨)

- **판정 기준** (스펙 §3): 최근 2주 내 3회 이상 실사용 또는 타 구성요소가 의존 → 유지·승격 /
  쓰는데 거슬림 → 수정·재설계 / 사용 0회·유지비용 0 → 보류 / 4주 무사용·유지비용 있음 → 폐기
- **모름(계측 대기)** 는 T1-2 사용 계측 데이터가 모이면 재판정한다. 추측으로 채우지 않는다.
- 마지막 갱신: 2026-07-19 (한글화·정리 세션 — 계측 1회차)

## Claude Code — `claude/`

| 구성요소 | 종류 | 출처 | 상태 | 판정 | 근거·메모 |
|---|---|---|---|---|---|
| brief-morning | 스킬 | 7loro 이식(적응) | 작동 | **수정·재설계 완료 (2026-07-19)** | 6/23 이후 무사용 — 원인: Hermes 중복+습관. 환경 프로파일(personal-laptop/work)로 재설계, github_issues 태스크 신설 |
| pkm | 스킬 | 7loro 이식(적응) | 작동 | 유지·승격 | 계측: Skill 8회+키워드 16회, 최근 07-19. TMDB 키 미설정(graceful skip) |
| pkm-collect | 스킬 | 7loro 이식(적응) | 작동 | **수정 완료 — 수동 폴백 (2026-07-19)** | 7/3 이후 무사용, 역할이 맥미니 Hermes로 이관 → 평시 경로 아님을 명시 |
| make-pr | 스킬 | 7loro 이식(적응) | 작동 | 유지·승격 | 계측: Skill 13회(최다), 최근 07-18~19. 주 사용처 contributions |
| review-claudemd | 스킬 | 7loro 이식(적응) | 제거됨 | **폐기 완료 (2026-07-19)** | 사용 기록 0회(있는지도 몰랐음) → monthly-review 절차 3으로 흡수 |
| monthly-review | 스킬 | 자작 (2026-07-19) | 작동 | 유지 | 로드맵 T1-2 실행체: 계측+INVENTORY 판정+CLAUDE.md 리뷰+링크 점검. 월 1회 |
| dotfiles-sync | 스킬 | 자작 (f08c58c) | 작동 | 유지 | 계측: Skill 9회+키워드 5회. 본 로드맵 커밋 규약 원천 |
| handoff | 스킬 | 자작 (a298490) | 작동 | 유지 | 6/29 이후 미사용이나 유지비용 0, HANDOFF.md 실적 → 인수인계 시점 문제 |
| obsidian-history | 스킬 | 자작 (1f83118 이전) | 작동 | 유지 | 계측: 7회(자동 트리거). pkm 계열 의존 |
| pkm-push | 스킬 | 자작 (094323b) | 작동 | 유지 | 계측: 슬래시 5회, 최근 07-18. inbox 적체 0(Hermes 실소비 확인) |
| workspace-flow | 스킬 | 자작 (79c9b54) | 작동 | **수정 완료 — 제안형 트리거 (2026-07-19)** | 7/1 이후 무사용 — 원인: 잊어버림. Claude가 먼저 제안하도록 전환 |
| knowledge-graph 훅 ×2 | 훅 | 7loro 이식 (ddc1f77) | 제거됨 | 폐기 완료 (2026-07-05) | no-op였고 llm-wiki와 경합 → 단일 경로화 |
| statusline-command.sh | statusline | 자작 (f08c58c, 이후 다수 수정) | 작동 | 유지 | 매 세션 사용. "누적토큰 Σ 다시 넣지 말 것"(HANDOFF) |
| settings.json | 설정 | 자작 | 작동 | 유지 | 2026-07-18 orca 훅 주입으로 심링크 파괴 → 07-19 훅 흡수+재링크(10e59e7). monthly-review 절차 4가 감시 |
| CLAUDE.md | 설정 | 자작 | 작동 | 유지 | 글로벌 메모리 |

## Hermes — `hermes/` (맥미니에서 사용)

| 구성요소 | 종류 | 출처 | 상태 | 판정 | 근거·메모 |
|---|---|---|---|---|---|
| hermes (허브) | 스킬 | 자작 (Claude pkm 스킬 파생, 7234170·5bba6b2) | 작동 | 유지 | llm-wiki 운영의 본체 — T2-1로 지식 경로 단일 소유자 |
| brief-morning | 스킬 | 자작 (Claude판 파생) | 작동 | 모름(계측 대기) | 맥미니 실물 확인은 세션 2 (스펙 §8) |
| daily-notes-automation | 스킬 | 자작 | 작동 | 모름(계측 대기) | 〃 |
| pkm-collect | 스킬 | 자작 (Claude판 파생) | 작동 | 유지 | 파이프라인의 맥미니 쪽 절반 |
| (공백) Hermes 코어 설정 | config·SOUL.md·cron | — | **dotfiles 밖** | T1-3에서 편입 | `~/.hermes/config.yaml`, SOUL.md, cron 정의가 미추적 — 재현 불가 상태 |

## 전통 dotfiles

| 구성요소 | 종류 | 출처 | 상태 | 판정 | 근거·메모 |
|---|---|---|---|---|---|
| git/ (gitconfig, gitignore) | 설정 | 자작 | 작동 | 유지 | |
| vim/vimrc | 설정 | 자작 | 작동 | 모름(계측 대기) | 실사용 빈도 불명 — 계측 곤란하면 보류 처리 |
| tmux/tmux.conf | 설정 | 자작 | 작동 | 모름(계측 대기) | 〃 |
| zsh/zshrc | 설정 | 자작 | 작동 | 유지 | cld alias 등 상시 사용 |
| ghostty/ (config, oceanic-dark) | 설정 | 자작 (8822f70) | 작동 | 유지 | 주 터미널 |
| cmux/cmux.json | 설정 | 자작 (230a68a) | 작동 | 모름(계측 대기) | |
| link.sh | 부트스트랩 | 자작 | 작동 | 수정·재설계 예정 | T1-4에서 머신 프로파일(main/laptop) 분기 |

## 판정 요약 (2026-07-19 — 사용 계측 1회차 반영)

- 계측(2026-07-19, monthly-review usage_audit.py 원형): transcript 14 프로젝트
  ·209MB + history.jsonl. 한계 — transcript는 cleanup으로 최근 ~1개월분.
- Claude 스킬: 유지·승격 2(make-pr, pkm) / 유지 4(dotfiles-sync, handoff,
  obsidian-history, pkm-push) / 수정·재설계 완료 3(brief-morning,
  workspace-flow, pkm-collect) / 폐기 완료 1(review-claudemd → monthly-review
  흡수) / 신설 1(monthly-review)
- 전통 dotfiles의 "모름"(vim/tmux/cmux)은 이 계측 방법(Claude transcript)의
  사각 — 보류 유지.
- 다음 재판정: **2026-08-19경 monthly-review 실행** (스킬이 예정일 경과를
  감지하면 먼저 제안한다)
