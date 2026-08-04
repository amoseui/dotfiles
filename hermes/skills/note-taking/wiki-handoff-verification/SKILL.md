---
name: wiki-handoff-verification
description: "Use when verifying cross-agent wiki handoffs."
version: 1.0.0
author: Hermes Agent + Amos
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [pkm, obsidian, knowledge-base, workflow, handoff]
    category: note-taking
---

# Cross-Agent Wiki Handoff Verification

공유 Obsidian/llm-wiki vault에서 Claude, Codex, Hermes 등 에이전트 간 인수인계가 실제로 기록·운영되고 있는지 원본과 live 상태로 검증한다. 파일명이 `handoff`가 아니어도 컴파일된 entity 페이지가 인수인계 표면일 수 있다.

## 절차

1. 활성 PKM 스킬의 `config.yaml`을 먼저 읽고 `vault_path`와 `wiki_dir`를 해석한다. legacy wiki 경로를 추측하지 않는다.
2. `SCHEMA.md`, `index.md`, `log.md` 최신 항목을 읽는다.
3. 에이전트 이름과 `인수인계`, `이어받`, `다음 작업`, `handoff`, `handover`, `continuation`을 내용으로 검색하고, `*인수*`, `*handoff*`, `*handover*` 파일명도 별도로 검색한다.
4. 후보마다 frontmatter, 상태/다음 작업, `## History`, outbound wikilink를 읽는다.
5. 후보가 `index.md`와 `log.md`에 등재됐는지 확인하고 `sources:`의 원문을 실제로 연다. 원문 스펙이 저장소 밖에 있으면 그 경로도 직접 확인한다.
6. 컴파일된 페이지와 원문 스펙의 날짜·상태가 다르면 둘 다 보고한다. 최신 명시 상태를 현재 상태로 설명하되 과거 원문을 덮어쓰지 않는다.
7. 결과를 `확인됨`, `근거`, `인수인계 범위`, `주의/남은 작업`으로 분리한다. 요약 페이지를 전체 transcript라고 부르지 않는다.
8. 확인만 요청받은 경우에는 wiki/index/log를 수정하지 않는다. 수정 요청이 있을 때만 normal llm-wiki write flow를 적용한다.

## live 상태 대조

사용자가 인수인계 이후 남은 작업을 묻는 경우, 페이지가 기록한 기대 상태와 현재 live 상태를 분리해 확인한다.

- `hermes --version`, `hermes status --all`, `hermes profile list/show`, `hermes cron list`, 관련 `hermes cron runs`, `hermes config check`, `hermes doctor`, 필요한 경우 `hermes skills list`를 사용한다.
- 서비스마다 supervisor 상태, 실제 listener/process, 로컬 health endpoint, 원격 proxy를 따로 확인한다. 건강한 port와 supervisor 관리 상태를 같은 것으로 보지 않는다.
- 작업 트리와 문서를 읽기 전용으로 대조하고, credential 파일·`.env`·`auth.json`·OAuth token은 읽지 않는다.
- delta 표에 기대 상태, 관찰 상태, 현재 영향, 근거, 다음 작업, 우선순위를 기록한다.
- `unknown` 실행은 성공/실패로 단정하지 않는다. 산출물 확인 또는 사용자 승인 후 재실행으로 검증한다.
- profile provider 불일치, missing skill reference, unmanaged service, no password/wildcard bind를 보안·가용성 우선으로 보고한다.
- P5 관련 handoff라면 review APPLY 상태, 저장된 query 수, entity 참조 흔적, 다음 관찰 실행을 함께 확인한다. 오래된 backlog와 최근 actionable 파일을 분리한다.

## 보고 경계

이 스킬은 기본적으로 audit 절차다. cron 실행, 서비스 재시작, profile 변경, package 설치, wiki/index/log 수정은 사용자가 명시적으로 수정·진행을 요청한 경우에만 수행한다. 수정 요청이 있으면 before-state를 먼저 남기고 최소 변경 후 live와 관리 저장소 diff를 검증한다.
