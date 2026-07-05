# 구성요소 인벤토리 (Component Inventory)

에이전트 인프라 로드맵 T1-1의 산출물이자, 모든 구성요소의 출처·상태·판정을 기록하는 대장.
(로드맵 스펙은 `docs/superpowers/specs/`에 로컬 보관 — gitignore됨)

- **판정 기준** (스펙 §3): 최근 2주 내 3회 이상 실사용 또는 타 구성요소가 의존 → 유지·승격 /
  쓰는데 거슬림 → 수정·재설계 / 사용 0회·유지비용 0 → 보류 / 4주 무사용·유지비용 있음 → 폐기
- **모름(계측 대기)** 는 T1-2 사용 계측 데이터가 모이면 재판정한다. 추측으로 채우지 않는다.
- 마지막 갱신: 2026-07-05 (세션 1)

## Claude Code — `claude/`

| 구성요소 | 종류 | 출처 | 상태 | 판정 | 근거·메모 |
|---|---|---|---|---|---|
| brief-morning | 스킬 | 7loro 이식(적응) | 작동 | 모름(계측 대기) | github_pr 기본 off — 켜기는 백로그 "소소한 켜기" |
| pkm | 스킬 | 7loro 이식(적응) | 작동 | 모름(계측 대기) | TMDB 키 미설정(graceful skip). obsidian-history에 의존 |
| pkm-collect | 스킬 | 7loro 이식(적응) | 작동 | 수정·재설계 후보 | 역할이 맥미니(Hermes판 pkm-collect)로 이동, 이 맥북은 pkm-push가 담당 — 맥북 쪽 존치 여부를 계측으로 판정 |
| make-pr | 스킬 | 7loro 이식(적응) | 작동 | 모름(계측 대기) | |
| review-claudemd | 스킬 | 7loro 이식(적응) | 작동 | 모름(계측 대기) | |
| dotfiles-sync | 스킬 | 자작 (f08c58c) | 작동 | 유지 | 본 로드맵 실행의 커밋 규약 원천, 상시 사용 |
| handoff | 스킬 | 자작 (a298490) | 작동 | 유지 | HANDOFF.md 갱신에 사용 실적 |
| obsidian-history | 스킬 | 자작 (1f83118 이전) | 작동 | 유지 | pkm 계열 스킬이 의존 |
| pkm-push | 스킬 | 자작 (094323b) | 작동 | 유지 | 크로스머신 파이프라인의 맥북 쪽 절반 (T2-2에서 자동화) |
| workspace-flow | 스킬 | 자작 (79c9b54) | 작동 | 모름(계측 대기) | |
| knowledge-graph 훅 ×2 | 훅 | 7loro 이식 (ddc1f77) | **no-op** (claude_agent_sdk 미설치) | **폐기 — T2-1 승인, 세션 1 집행** | llm-wiki(Hermes, 운영 중)와 경합 → 단일 경로화. 부활 대안은 스펙 §5 T2-1에서 기각 |
| statusline-command.sh | statusline | 자작 (f08c58c, 이후 다수 수정) | 작동 | 유지 | 매 세션 사용. "누적토큰 Σ 다시 넣지 말 것"(HANDOFF) |
| settings.json | 설정 | 자작 | 작동 | 유지 | live와 심링크로 일치 |
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

## 판정 요약 (2026-07-05)

- 유지 12 / 폐기 1(knowledge-graph 훅) / 수정·재설계 2(pkm-collect 맥북판, link.sh) / 모름(계측 대기) 10 / dotfiles 편입 예정 1(Hermes 코어 설정, T1-3)
- 다음 재판정: T1-2 계측 4주 데이터 확보 후 (스펙 §7 세션 5+)
