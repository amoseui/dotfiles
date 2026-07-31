# 구성요소 인벤토리 (Component Inventory)

에이전트 인프라 로드맵 T1-1의 산출물이자, 모든 구성요소의 출처·상태·판정을 기록하는 대장.
(로드맵 스펙은 `docs/superpowers/specs/`에 로컬 보관 — gitignore됨)

- **판정 기준** (스펙 §3): 최근 2주 내 3회 이상 실사용 또는 타 구성요소가 의존 → 유지·승격 /
  쓰는데 거슬림 → 수정·재설계 / 사용 0회·유지비용 0 → 보류 / 4주 무사용·유지비용 있음 → 폐기
- **모름(계측 대기)** 는 T1-2 사용 계측 데이터가 모이면 재판정한다. 추측으로 채우지 않는다.
- 마지막 갱신: 2026-07-31 (4존 마이그레이션 반영)

## Claude Code — `claude/`

| 구성요소 | 종류 | 출처 | 상태 | 판정 | 근거·메모 |
|---|---|---|---|---|---|
| brief-morning | 스킬 | 7loro 이식(적응) | 작동 | **수정·재설계 완료 (2026-07-19)** | 6/23 이후 무사용 — 원인: Hermes 중복+습관. 환경 프로파일(personal-laptop/work)로 재설계, github_issues 태스크 신설. 2026-07-31 4존 마이그레이션 반영 |
| pkm | 스킬 | 7loro 이식(적응) | 작동 | 유지·승격 | 계측: Skill 8회+키워드 16회, 최근 07-19. TMDB 키 미설정(graceful skip). 2026-07-31 4존 마이그레이션 반영 |
| pkm-collect | 스킬 | 7loro 이식(적응) | 작동 | **수정 완료 — 수동 폴백 (2026-07-19)** | 7/3 이후 무사용, 역할이 맥미니 Hermes로 이관 → 평시 경로 아님을 명시. 2026-07-31 4존 마이그레이션 반영 |
| make-pr | 스킬 | 7loro 이식(적응) | 작동 | 유지·승격 | 계측: Skill 13회(최다), 최근 07-18~19. 주 사용처 contributions. 2026-07-31 4존 마이그레이션 반영 |
| review-claudemd | 스킬 | 7loro 이식(적응) | 제거됨 | **폐기 완료 (2026-07-19)** | 사용 기록 0회(있는지도 몰랐음) → monthly-review 절차 3으로 흡수 |
| monthly-review | 스킬 | 자작 (2026-07-19) | 작동 | 유지 | 로드맵 T1-2 실행체: 계측+INVENTORY 판정+CLAUDE.md 리뷰+링크 점검. 월 1회 |
| dotfiles-sync | 스킬 | 자작 (f08c58c) | 작동 | 유지 | 계측: Skill 9회+키워드 5회. 본 로드맵 커밋 규약 원천 |
| handoff | 스킬 | 자작 (a298490) | 작동 | 유지 | 6/29 이후 미사용이나 유지비용 0, HANDOFF.md 실적 → 인수인계 시점 문제 |
| obsidian-history | 스킬 | 자작 (1f83118 이전) | 작동 | 유지 | 계측: 7회(자동 트리거). pkm 계열 의존. 2026-07-31 4존 마이그레이션 반영 |
| pkm-push | 스킬 | 자작 (094323b) | 작동 | 유지 | 계측: 슬래시 5회, 최근 07-18. inbox 적체 0(Hermes 실소비 확인). 2026-07-31 4존 마이그레이션 반영 |
| workspace-flow | 스킬 | 자작 (79c9b54) | 작동 | **수정 완료 — 제안형 트리거 (2026-07-19)** | 7/1 이후 무사용 — 원인: 잊어버림. Claude가 먼저 제안하도록 전환 |
| knowledge-graph 훅 ×2 | 훅 | 7loro 이식 (ddc1f77) | 제거됨 | 폐기 완료 (2026-07-05) | no-op였고 llm-wiki와 경합 → 단일 경로화 |
| statusline-command.sh | statusline | 자작 (f08c58c, 이후 다수 수정) | 작동 | 유지 | 매 세션 사용. "누적토큰 Σ 다시 넣지 말 것"(HANDOFF) |
| settings.json | 설정 | 자작 | 작동 | 유지 | 2026-07-18 orca 훅 주입으로 심링크 파괴 → 07-19 훅 흡수+재링크(10e59e7). monthly-review 절차 4가 감시 |
| CLAUDE.md | 설정 | 자작 | 작동 | 유지 | 글로벌 메모리 |

## Hermes — `hermes/` (맥미니에서 사용)

| 구성요소 | 종류 | 출처 | 상태 | 판정 | 근거·메모 |
|---|---|---|---|---|---|
| hermes (허브) | 스킬 | 자작 (Claude pkm 스킬 파생, 7234170·5bba6b2) | 작동 | 유지 | llm-wiki 운영의 본체 — T2-1로 지식 경로 단일 소유자. 2026-07-31 4존 마이그레이션 반영 |
| brief-morning | 스킬 | 자작 (Claude판 파생) | 작동 | 모름(계측 대기) | 맥미니 실물 확인은 세션 2 (스펙 §8). 2026-07-31 4존 마이그레이션 반영 |
| daily-notes-automation | 스킬 | 자작 | 작동 | 모름(계측 대기) | 〃. 2026-07-31 4존 마이그레이션 반영 |
| pkm-collect | 스킬 | 자작 (Claude판 파생) | 작동 | 유지 | 파이프라인의 맥미니 쪽 절반. 2026-07-31 4존 마이그레이션 반영 |
| Hermes 코어 설정 | config·SOUL.md·cron·script | 자작 | **dotfiles 백업됨** | 유지 | 민감값은 `${ENV_VAR}`로 치환. note-taking 스킬(hermes·daily-notes-automation·pkm-collect·brief-morning)은 dotfiles로 symlink됨(편집이 곧 반영) — bootstrap 복사는 atomic-write 대상인 `~/.hermes/cron/jobs.json`·`~/.hermes/config.yaml`뿐(이전 표기 "symlink 대신 bootstrap 복사"는 부정확 — Task 7b 실측으로 정정, 2026-07-31) |
| 메모 큐레이션 (일요일 10:00) | cron | 자작 (2026-07-31) | 신설 | 모름(계측 대기) | ID `8331351e1726`. Task 11 live-verified(2026-07-31) — `hermes cron list` 8/8 확인 |
| 위키 큐레이터 정합성 (일요일 22:00) | cron | 자작 (2026-07-31) | 신설 | 모름(계측 대기) | ID `172e57bcec4e`. Task 11 live-verified(2026-07-31) — `hermes cron list` 8/8 확인 |

## 전통 dotfiles

| 구성요소 | 종류 | 출처 | 상태 | 판정 | 근거·메모 |
|---|---|---|---|---|---|
| git/ (gitconfig, gitignore) | 설정 | 자작 | 작동 | 유지 | |
| vim/vimrc | 설정 | 자작 | 작동 | 모름(계측 대기) | 실사용 빈도 불명 — 계측 곤란하면 보류 처리 |
| tmux/tmux.conf | 설정 | 자작 | 작동 | 모름(계측 대기) | 〃 |
| zsh/zshrc | 설정 | 자작 | 작동 | 유지 | cld alias 등 상시 사용 |
| ghostty/ (config, oceanic-dark) | 설정 | 자작 (8822f70) | 작동 | 유지 | 주 터미널 |
| cmux/cmux.json | 설정 | 자작 (230a68a) | 작동 | 모름(계측 대기) | |
| link.sh + scripts/bootstrap-mac.sh | 부트스트랩 | 자작 | 작동 | 수정 완료 | Mac Studio 복원, timestamp 백업, dry-run, atomic-write 파일은 복사 |

## 판정 요약 (2026-07-19 — 사용 계측 1회차 반영)

- 계측(2026-07-19, monthly-review usage_audit.py 원형): transcript 14 프로젝트
  ·209MB + history.jsonl. 한계 — transcript는 cleanup으로 최근 ~1개월분.
- Claude 스킬: 유지·승격 2(make-pr, pkm) / 유지 4(dotfiles-sync, handoff,
  obsidian-history, pkm-push) / 수정·재설계 완료 3(brief-morning,
  workspace-flow, pkm-collect) / 폐기 완료 1(review-claudemd → monthly-review
  흡수) / 신설 1(monthly-review)
- 전통 dotfiles의 "모름"(vim/tmux/cmux)은 이 계측 방법(Claude transcript)의
  사각 — 보류 유지.
- **환경 미완(마이그레이션 밖)** — 4존 마이그레이션 P3 진행 중 발견, 마이그레이션
  자체의 결함은 아니나 다음 재판정의 A 소비 계측 해석에 영향을 줄 수 있어 기록
  (2026-07-31):
  - Google OAuth 미설정(`~/.hermes/google-accounts/` 부재) — 아침/밤 daily-note의
    캘린더·메일 섹션은 폴백 동작 중.
  - `READWISE_TOKEN` 부재 — backlog 소진 job이 Reader 소스 없이 부분 기능으로 동작.
  - Todoist 연동 미확인 — 출력이 "없음"인 것이 정상 0건인지 인증 실패인지 로그만으로
    구분 불가.
  - Chromium docs job의 완료-알림 delivery가 origin platform `webui`로 실패(사전
    존재 — 이번 마이그레이션 이전부터 있던 문제, 작업 실행 자체는 정상).
- 다음 재판정: **2026-08-31 monthly-review 예정** (P5 관찰 1~2주 + 월간 주기;
  스킬이 예정일 경과를 감지하면 먼저 제안한다) — A 소비 계측 확인 항목: wiki/queries
  생성 수, entities 참조 흔적(transcript), agents/review 처리율(생성 대비 APPLY 비율).
