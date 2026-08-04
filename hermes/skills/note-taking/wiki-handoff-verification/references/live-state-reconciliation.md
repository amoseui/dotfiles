# Live-State Reconciliation After a Wiki Handoff

## Read-only probe order

- handoff 페이지, 원문 스펙/계획, `index.md`, 최근 `log.md`를 읽어 기대 상태·날짜·다음 작업을 기록한다.
- Hermes는 `hermes --version`, `status --all`, `profile list/show`, `cron list`, 관련 `cron runs`, `config check`, `doctor`, 필요한 경우 `skills list`를 사용한다.
- 서비스는 supervisor, listener/process, local health, remote routing을 따로 확인한다.
- Git status와 문서·백업 상태를 읽기 전용으로 대조하고 `.env`, `auth.json`, OAuth 파일, API key는 읽지 않는다.

## Delta 해석

| 기대 | 관찰 | 영향 | 다음 작업 |
|---|---|---|---|
| profile이 provider X | provider Y | 동작/비용/개인정보 경계 차이 | 의도 확인 후 변경 또는 문서화 |
| scheduled run 완료 | `unknown` | side effect 미확정 | 산출물 확인 또는 승인 후 재실행 |
| job skill 설치됨 | catalog에 없음 | 의도한 규칙 미적용 가능 | 설치·백업 또는 stale 참조 제거 |
| supervisor가 관리 | port만 healthy | 재부팅 복구 불확실 | supervisor 소유로 정상화 |
| loopback + 보호 | wildcard/no password | LAN 노출 위험 | loopback 바인딩과 접근 경계 확인 |
| P5 사용 증거 있음 | query/APPLY 없음 | 도입 검증 안 됨 | 최근 샘플을 작게 처리 후 관찰 |
| 문서가 현재 상태 설명 | live보다 오래됨 | 다음 인수인계 오염 | 의도 확정 후 문서 갱신 |

`unknown`은 성공도 실패도 아니다. 오래된 backlog와 최근 actionable 파일을 분리하고, 사용자 의도에 좌우되는 profile routing은 별도 결정으로 보고한다.
