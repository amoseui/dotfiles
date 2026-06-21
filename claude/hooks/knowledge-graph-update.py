#!/usr/bin/env python3
"""
Stop hook: Claude Code 세션 종료 시 transcript를 분석하여
가치 있는 지식을 PKM vault의 마크다운 파일로 자동 기록.

- KNOWLEDGE_GRAPH_SKIP=1 환경변수로 재귀 방지
- KNOWLEDGE_GRAPH_PATH 환경변수로 지식 그래프 경로 지정
- os.fork()로 백그라운드 실행 (부모 즉시 종료)
- claude_agent_sdk (sonnet, effort=high)로 가치 판단
- 새 파일 생성 또는 기존 파일 업데이트
- INDEX.md + 프로젝트 _index.md 인덱스 관리
"""

import asyncio
import json
import os
import re
import subprocess
import sys
import traceback
from datetime import datetime
from pathlib import Path

# claude_agent_sdk는 선택적 의존성. 미설치 시 훅이 조용히 no-op 하도록 가드한다.
# (설치: pip install claude-agent-sdk)
try:
    from claude_agent_sdk import (
        AssistantMessage,
        ClaudeAgentOptions,
        ResultMessage,
        TextBlock,
        query,
    )
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False

LOG_FILE = Path("/tmp/knowledge-graph-update.log")

# 프로젝트로 취급하지 않을 디렉토리명 (git remote 없이 디렉토리명 폴백 시 필터링)
IGNORED_PROJECTS = {
    "Documents", "Downloads", "Desktop", "Pictures", "Music", "Movies",
    "Library", "Applications", "Public", "Home",
    "claude", "resources", "skills", "dotfiles",
}


def log(message: str) -> None:
    """로그 파일에 메시지 기록"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] {message}\n")


def extract_conversation(transcript_path: str) -> str | None:
    """전체 user+assistant 메시지 추출, 최대 5000자 (최근 대화 우선)"""
    try:
        with open(transcript_path, "r") as f:
            lines = f.readlines()

        messages = []
        for line in lines:
            try:
                data = json.loads(line)
                message = data.get("message", {})
                role = message.get("role")
                if role not in ("user", "assistant"):
                    continue

                content = message.get("content", [])
                if isinstance(content, str):
                    text = content
                elif isinstance(content, list):
                    text_parts = [
                        item.get("text", "")
                        for item in content
                        if isinstance(item, dict) and item.get("type") == "text"
                    ]
                    text = "\n".join(text_parts)
                else:
                    continue

                if text.strip():
                    messages.append(f"[{role}]\n{text.strip()}")
            except json.JSONDecodeError:
                continue

        if not messages:
            return None

        # 최대 3000자, 최근 대화 우선 (뒤에서부터 채움)
        result_parts = []
        total_len = 0
        for msg in reversed(messages):
            if total_len + len(msg) + 4 > 5000:  # +4: 구분자 여유
                # 남은 공간만큼 잘라서 추가
                remaining = 5000 - total_len - 4
                if remaining > 100:
                    result_parts.append(msg[:remaining] + "...")
                break
            result_parts.append(msg)
            total_len += len(msg) + 4

        result_parts.reverse()
        return "\n\n".join(result_parts)
    except Exception as e:
        log(f"대화 추출 오류: {e}\n{traceback.format_exc()}")
        return None


def identify_project(cwd: str) -> str:
    """프로젝트 식별: git remote URL 우선, 디렉토리명 폴백"""
    try:
        result = subprocess.run(
            ["git", "-C", cwd, "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            url = result.stdout.strip()
            name = os.path.basename(url)
            # .git 제거
            if name.endswith(".git"):
                name = name[:-4]
            if name:
                return name
    except Exception:
        pass

    return os.path.basename(cwd)


def ensure_directories(kg_path: Path, project_name: str) -> None:
    """common/, projects/{name}/ 디렉토리 및 INDEX.md 자동 생성"""
    (kg_path / "common").mkdir(parents=True, exist_ok=True)
    (kg_path / "projects" / project_name).mkdir(parents=True, exist_ok=True)

    # INDEX.md 생성 (없을 때만)
    index_file = kg_path / "INDEX.md"
    if not index_file.exists():
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        index_file.write_text(
            f"---\nname: Knowledge Graph Index\n"
            f"description: 전체 지식 그래프 인덱스 — common 및 프로젝트별 지식 목록\n"
            f"type: reference\n"
            f"created: {now}\nmodified: {now}\ntags:\n  - personal\n  - dev\n---\n\n"
            "# Knowledge Graph Index\n\n## Common\n\n## Projects\n",
            encoding="utf-8",
        )
        log(f"INDEX.md 생성: {index_file}")

    # 프로젝트 _index.md 생성 (없을 때만)
    project_index = kg_path / "projects" / project_name / "_index.md"
    if not project_index.exists():
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        project_index.write_text(
            f"---\nname: {project_name}\n"
            f"description: 프로젝트 {project_name}의 지식 인덱스\n"
            f"type: reference\n"
            f"created: {now}\nmodified: {now}\ntags:\n  - personal\n  - dev\n---\n\n"
            f"# {project_name}\n"
            f"- **식별자**: {project_name}\n\n"
            "## 지식 목록\n",
            encoding="utf-8",
        )
        log(f"프로젝트 _index.md 생성: {project_index}")


def read_index(kg_path: Path) -> str:
    """INDEX.md 내용 읽기"""
    index_file = kg_path / "INDEX.md"
    if index_file.exists():
        return index_file.read_text(encoding="utf-8")
    return ""


def _try_recover_json(text: str) -> list[dict]:
    """잘린 JSON 배열에서 완전한 객체들만 추출"""
    recovered = []
    # 개별 {...} 객체를 찾아서 파싱 시도
    depth = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start >= 0:
                try:
                    obj = json.loads(text[start : i + 1])
                    # 필수 필드 확인
                    if "title" in obj and "content" in obj:
                        recovered.append(obj)
                except json.JSONDecodeError:
                    pass
                start = -1
    if recovered:
        log(f"부분 복구 성공: {len(recovered)}개 객체")
    else:
        log(f"부분 복구 실패\n응답: {text[:500]}")
    return recovered


SYSTEM_PROMPT_TEMPLATE = """너는 Claude Code 세션 대화를 분석하여 가치 있는 지식을 추출하는 역할이야.

## 작업
1. 대화 내용을 분석해서 기록할 가치가 있는 지식이 있는지 판단
2. 가치가 있다면 JSON 형식으로 지식을 추출
3. 가치가 없다면 빈 JSON 배열 반환
4. 빈약한 지식보다 기록하지 않는 것이 낫다. 확신이 없으면 빈 배열을 반환해.

## 리트머스 테스트 (모든 항목이 YES여야 기록)
기록 전 아래 3개 질문에 모두 YES인지 확인해:
1. **놀라움**: 경험 있는 개발자도 모를 수 있는 비직관적 내용인가? (NO → 기록하지 마)
2. **재사용성**: 6개월 후 같은 상황을 만나면 이 노트를 검색할까? (NO → 기록하지 마)
3. **구체성**: 이 노트만 읽고 바로 행동할 수 있나? (NO → 기록하지 마)

## 가치 판단 기준
기록할 가치가 있는 것 (리트머스 테스트 통과 필수):
- 시행착오 끝에 발견한 해결법 (삽질 30분 이상 했을 법한 것만)
- API/라이브러리의 비직관적 동작 (공식 문서에 없거나 찾기 어려운 것)
- 디버깅 패턴/노하우 (구체적 재현 조건과 해결법 포함)

기록할 가치가 없는 것:
- 단순 파일 생성/편집/정리 작업
- 이미 공식 문서에 있는 기본 사항
- 일회성 작업 (특정 데이터 조회, 문서 작성, 설정 변경 등)
- 단순 질의응답 (인사, 설명 요청 등)
- 구체적 해결법 없이 "문제가 있었다" 정도의 피상적 내용
- 프로젝트 설계 결정 (아키텍처, UI 패턴, 기술 스택 선택 등) — 코드/커밋에 이미 기록됨
- 워크플로우/프로세스 정리 (커밋 규칙, PR 패턴, 스킬 사용법 등) — CLAUDE.md나 스킬에 있어야 할 내용
- 특정 도메인 지식 (법률, 언어 학습 등) — 범용 개발 지식이 아닌 것
- Claude/AI 도구 메타 지식 (스킬 동작 원리, 에이전트 패턴 등)

## 수량 제한
한 세션에서 최대 2개까지만 추출. 3개 이상이면 가장 가치 높은 2개만 선택.

## 중복 판단 기준 (매우 중요)
아래 기존 지식 인덱스를 반드시 확인하고:
- **정확히 같은 제목**: 당연히 스킵
- **유사한 주제**: 제목이 달라도 같은 문제/패턴을 다루면 중복. 새로 만들지 말 것.
  예) "GitHub API 답글 jq 패턴" vs "GitHub PR 봇 답글 jq 패턴" → 중복
- **기존 지식의 확장**: 새 내용이 기존 노트의 보충이면 existing_file로 지정해서 추가

## 출력 형식
반드시 아래 JSON 형식으로만 응답. 다른 텍스트 없이 JSON만 반환.
content는 500자 이내로 작성하되, 아래를 반드시 포함:
- troubleshooting: 문제 상황 + 원인 + 구체적 해결 단계
- tip: 핵심 요약 + 적용 방법 또는 코드 예시
- convention: 규칙 + 왜 그런지 이유 + 예시
- context: 배경 + 의사결정 근거
줄바꿈은 \\n으로 표현. 테이블, 코드 블록 등 복잡한 마크다운은 사용하지 말 것.

가치 있는 지식이 없을 때:
[]

가치 있는 지식이 있을 때:
[
  {{
    "type": "troubleshooting | tip | context | convention",
    "scope": "common | project",
    "title": "한글 파일명 (예: Obsidian Bases 날짜 타입 정리)",
    "content": "500자 이내. 구체적 해결법/예시 포함 필수.",
    "related": [],
    "existing_file": null
  }}
]

## 기존 지식 인덱스
아래는 이미 기록된 지식 목록이야. 중복되지 않게 해:
{index_content}"""


async def _extract_knowledge_async(
    conversation: str, index_content: str
) -> list[dict]:
    """claude_agent_sdk 호출, JSON 응답 파싱"""
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(index_content=index_content)

    options = ClaudeAgentOptions(
        model="sonnet",
        system_prompt=system_prompt,
        tools=[],
        allowed_tools=[],
        max_turns=1,
        thinking={"type": "disabled"},
        effort="high",
        env={"KNOWLEDGE_GRAPH_SKIP": "1"},
    )

    response_text = ""
    async for message in query(
        prompt=f"아래 대화를 분석해서 가치 있는 지식을 추출해:\n\n{conversation}",
        options=options,
    ):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    response_text += block.text
        elif isinstance(message, ResultMessage):
            break

    if not response_text.strip():
        log("SDK 응답이 비어있음")
        return []

    # ```json ... ``` 래핑 제거
    cleaned = response_text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", cleaned)
    if match:
        cleaned = match.group(1).strip()

    try:
        result = json.loads(cleaned)
        if isinstance(result, list):
            return result
        log(f"JSON 응답이 배열이 아님: {type(result)}")
        return []
    except json.JSONDecodeError as e:
        log(f"JSON 파싱 실패, 부분 복구 시도: {e}")
        return _try_recover_json(cleaned)


def extract_knowledge(conversation: str, index_content: str) -> list[dict]:
    """동기 래퍼"""
    try:
        return asyncio.run(_extract_knowledge_async(conversation, index_content))
    except Exception as e:
        log(f"지식 추출 실패: {e}\n{traceback.format_exc()}")
        return []


def _build_note_content(knowledge: dict) -> str:
    """유형별 마크다운 본문 생성"""
    k_type = knowledge.get("type", "tip")
    content = knowledge.get("content", "")
    related = knowledge.get("related", [])

    # content에 이미 ## 섹션이 포함되어 있으면 그대로 사용
    if "## " in content:
        body = content
    else:
        # content를 유형 헤더 아래에 배치 (빈 섹션 강제 생성하지 않음)
        if k_type == "troubleshooting":
            body = f"## 문제와 해결\n\n{content}\n"
        elif k_type == "convention":
            body = f"## 규칙\n\n{content}\n"
        else:
            # tip, context
            body = f"## 요약\n\n{content}\n"

    # 관련 링크 추가
    if related:
        links = "\n".join(f"- [[{r}]]" for r in related)
        body += f"\n## 관련\n\n{links}\n"

    return body


def write_knowledge_note(
    kg_path: Path, project_name: str, knowledge: dict
) -> str | None:
    """마크다운 파일 쓰기 (새 생성 or 기존 업데이트). 파일명 반환."""
    scope = knowledge.get("scope", "project")
    title = knowledge.get("title", "제목 없음")
    existing = knowledge.get("existing_file")

    # common 우선 중복 방지: 파일 레벨
    check_name = f"{existing or title}.md"
    if scope == "project":
        if (kg_path / "common" / check_name).exists():
            log(f"common에 이미 존재, project 저장 스킵: {title}")
            return None
    elif scope == "common":
        project_file = kg_path / "projects" / project_name / check_name
        if project_file.exists():
            project_file.unlink()
            log(f"common 우선: project 중복 파일 삭제: {project_file}")

    if scope == "common":
        target_dir = kg_path / "common"
    else:
        target_dir = kg_path / "projects" / project_name

    if existing:
        # 기존 파일에 추가
        target_file = target_dir / f"{existing}.md"
        if not target_file.exists():
            # common에도 찾아보기
            alt = kg_path / "common" / f"{existing}.md"
            if alt.exists():
                target_file = alt
            else:
                # 다른 프로젝트 폴더에서 검색
                for p in (kg_path / "projects").iterdir():
                    candidate = p / f"{existing}.md"
                    if candidate.exists():
                        target_file = candidate
                        break

        if target_file.exists():
            # 기존 내용에 추가
            current = target_file.read_text(encoding="utf-8")
            new_content = knowledge.get("content", "")
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # modified 업데이트
            current = re.sub(
                r"modified: .+",
                f"modified: {now}",
                current,
                count=1,
            )

            # 본문 끝에 새 내용 추가
            current = current.rstrip() + f"\n\n---\n\n### 추가 ({now[:10]})\n\n{new_content}\n"
            target_file.write_text(current, encoding="utf-8")
            log(f"기존 파일 업데이트: {target_file}")
            return existing
        else:
            log(f"기존 파일 미발견, 새 파일로 생성: {existing}")
            # 아래에서 새 파일로 생성

    # 새 파일 생성
    filename = f"{title}.md"
    target_file = target_dir / filename
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    body = _build_note_content(knowledge)

    # description 생성: content 첫 줄에서 120자
    desc_text = knowledge.get("content", title)
    for line in desc_text.split("\\n"):
        line = line.strip().lstrip("#").strip().lstrip("- ").strip()
        if len(line) > 10:
            desc_text = line[:120]
            break

    k_type_str = knowledge.get("type", "tip")
    frontmatter = (
        f"---\nname: {title}\n"
        f"description: {desc_text}\n"
        f"type: {k_type_str}\n"
        f"created: {now}\nmodified: {now}\n"
        f"tags:\n  - personal\n  - dev\n---\n"
    )

    target_file.write_text(f"{frontmatter}\n{body}", encoding="utf-8")
    log(f"새 파일 생성: {target_file}")
    return title


def _remove_entry_from_index(file_path: Path, title: str) -> None:
    """인덱스 파일에서 [title](...) 또는 [[title]] 항목 제거"""
    if not file_path.exists():
        return
    content = file_path.read_text(encoding="utf-8")
    # 새 포맷 [Title](path) 또는 구 포맷 [[Title]]
    if f"[{title}](" not in content and f"[[{title}]]" not in content:
        return
    # 새 포맷 제거
    pattern_new = rf"- \[{re.escape(title)}\]\([^\)]*\)[^\n]*\n?"
    new_content = re.sub(pattern_new, "", content)
    # 구 포맷 제거 (호환성)
    pattern_old = rf"- \[\[{re.escape(title)}\]\][^\n]*\n?"
    new_content = re.sub(pattern_old, "", new_content)
    new_content = re.sub(r"\n{3,}", "\n\n", new_content)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_content = re.sub(r"modified: .+", f"modified: {now}", new_content, count=1)
    file_path.write_text(new_content, encoding="utf-8")
    log(f"인덱스에서 항목 제거: {title} from {file_path}")


def update_index(
    kg_path: Path, project_name: str, knowledge: dict
) -> None:
    """INDEX.md, 프로젝트 _index.md 업데이트"""
    scope = knowledge.get("scope", "project")
    title = knowledge.get("title", "제목 없음")
    k_type = knowledge.get("type", "tip")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # description 생성
    desc_text = knowledge.get("content", title)
    for line in desc_text.split("\\n"):
        line = line.strip().lstrip("#").strip().lstrip("- ").strip()
        if len(line) > 10:
            desc_text = line[:120]
            break

    if scope == "common":
        entry_path = f"common/{title}.md"
    else:
        entry_path = f"projects/{project_name}/{title}.md"
    # 괄호/대괄호가 있으면 앵글 브라켓 구문 사용
    if "(" in entry_path or ")" in entry_path or "[" in entry_path or "]" in entry_path:
        entry = f"- [{title}](<{entry_path}>) — {desc_text}"
    else:
        entry = f"- [{title}]({entry_path}) — {desc_text}"

    # INDEX.md 업데이트
    index_file = kg_path / "INDEX.md"
    if index_file.exists():
        content = index_file.read_text(encoding="utf-8")

        # 중복 확인 (새/구 포맷 모두)
        if f"[{title}](" in content or f"[[{title}]]" in content:
            log(f"INDEX.md에 이미 존재: {title}")
        else:
            # modified 업데이트
            content = re.sub(
                r"modified: .+",
                f"modified: {now}",
                content,
                count=1,
            )

            if scope == "common":
                content = content.replace(
                    "\n## Projects",
                    f"\n{entry}\n\n## Projects",
                )
            else:
                if f"### {project_name}" not in content:
                    content = content.rstrip() + f"\n\n### {project_name}\n{entry}\n"
                else:
                    pattern = rf"(### {re.escape(project_name)}\n)"
                    content = re.sub(
                        pattern,
                        rf"\1{entry}\n",
                        content,
                    )

            index_file.write_text(content, encoding="utf-8")
            log(f"INDEX.md 업데이트: {title}")

    # 프로젝트 _index.md 업데이트 (project 범위일 때)
    if scope == "project":
        project_index = kg_path / "projects" / project_name / "_index.md"
        if project_index.exists():
            content = project_index.read_text(encoding="utf-8")

            if f"[{title}](" in content or f"[[{title}]]" in content:
                log(f"프로젝트 _index.md에 이미 존재: {title}")
            else:
                content = re.sub(
                    r"modified: .+",
                    f"modified: {now}",
                    content,
                    count=1,
                )

                proj_entry = f"- [{title}]({title}.md) — {desc_text}"
                content = content.rstrip() + f"\n{proj_entry}\n"
                project_index.write_text(content, encoding="utf-8")
                log(f"프로젝트 _index.md 업데이트: {title}")

    # common 범위일 때: project 쪽 인덱스에서 중복 제거
    if scope == "common":
        _remove_entry_from_index(
            kg_path / "projects" / project_name / "_index.md", title
        )
        # INDEX.md의 Projects 섹션에서도 제거
        if index_file.exists():
            content = index_file.read_text(encoding="utf-8")
            projects_marker = "\n## Projects"
            idx = content.find(projects_marker)
            if idx >= 0:
                before = content[: idx + len(projects_marker)]
                after = content[idx + len(projects_marker) :]
                pat = rf"- \[\[{re.escape(title)}\]\][^\n]*\n?"
                new_after, count = re.subn(pat, "", after)
                if count > 0:
                    new_after = re.sub(r"\n{3,}", "\n\n", new_after)
                    index_file.write_text(before + new_after, encoding="utf-8")
                    log(f"INDEX.md Projects 섹션에서 중복 제거: {title}")


def background_process(
    transcript_path: str, cwd: str, kg_path: Path, project_name: str
) -> None:
    """메인 백그라운드 로직"""
    try:
        log(f"백그라운드 프로세스 시작 (PID: {os.getpid()})")
        log(f"프로젝트: {project_name}, CWD: {cwd}")

        # 디렉토리 확인/생성
        ensure_directories(kg_path, project_name)

        # 대화 추출
        conversation = extract_conversation(transcript_path)
        if not conversation:
            log("대화 내용이 비어있음, 건너뜀")
            return

        log(f"대화 추출 완료: {len(conversation)}자")

        # 인덱스 읽기
        index_content = read_index(kg_path)

        # 프로젝트 _index.md 내용도 포함
        project_index_file = kg_path / "projects" / project_name / "_index.md"
        if project_index_file.exists():
            index_content += "\n\n" + project_index_file.read_text(encoding="utf-8")

        # 지식 추출
        knowledges = extract_knowledge(conversation, index_content)

        if not knowledges:
            log("추출된 지식 없음 (가치 판단: 기록 불필요)")
            return

        log(f"추출된 지식: {len(knowledges)}개")

        # 파일 쓰기 및 인덱스 업데이트
        for k in knowledges:
            title = write_knowledge_note(kg_path, project_name, k)
            if title:
                update_index(kg_path, project_name, k)

        log(f"지식 기록 완료: {len(knowledges)}개")
    except Exception as e:
        log(f"백그라운드 프로세스 오류: {e}\n{traceback.format_exc()}")


def main() -> None:
    log("=== knowledge-graph-update 시작 ===")

    # 선택적 의존성 가드: claude_agent_sdk 미설치면 조용히 종료(세션 블로킹 없음)
    if not SDK_AVAILABLE:
        log("claude_agent_sdk 미설치, 건너뜀 (pip install claude-agent-sdk)")
        return

    # 환경변수 가드: KNOWLEDGE_GRAPH_PATH
    kg_path_str = os.environ.get("KNOWLEDGE_GRAPH_PATH", "")
    if not kg_path_str:
        log("KNOWLEDGE_GRAPH_PATH 미설정, 건너뜀")
        return

    # 재귀 방지
    if os.environ.get("KNOWLEDGE_GRAPH_SKIP") == "1":
        log("KNOWLEDGE_GRAPH_SKIP=1, 건너뜀")
        return

    # stdin에서 hook 데이터 읽기
    try:
        hook_input = json.loads(sys.stdin.read())
    except Exception as e:
        log(f"stdin 읽기 실패: {e}\n{traceback.format_exc()}")
        return

    if hook_input.get("stop_hook_active"):
        log("stop_hook_active=True, 건너뜀")
        return

    # transcript 경로 추출
    transcript_path = hook_input.get("transcript_path")
    if not transcript_path:
        log("transcript_path 없음, 건너뜀")
        return
    transcript_path = os.path.expanduser(transcript_path)

    # CWD 추출
    cwd = hook_input.get("cwd", os.getcwd())

    # 경로 확장
    kg_path = Path(os.path.expanduser(kg_path_str))
    if not kg_path.exists():
        kg_path.mkdir(parents=True, exist_ok=True)
        log(f"지식 그래프 루트 디렉토리 생성: {kg_path}")

    # 프로젝트 식별
    project_name = identify_project(cwd)
    log(f"프로젝트 식별: {project_name}")

    # 블랙리스트 필터링
    if project_name in IGNORED_PROJECTS:
        log(f"블랙리스트 프로젝트, 건너뜀: {project_name}")
        return

    # stdin은 fork 전에 이미 읽었으므로 안전
    # 백그라운드 분기: 부모는 즉시 종료하여 훅 대기 해제
    child_pid = os.fork()
    if child_pid > 0:
        log(f"백그라운드 자식 프로세스 생성: PID {child_pid}, 부모 즉시 종료")
        sys.exit(0)

    # 자식 프로세스: 새 세션에서 나머지 작업 수행
    os.setsid()
    # 표준 입출력 분리 (부모 종료 후 파이프 깨짐 방지)
    devnull = os.open(os.devnull, os.O_RDWR)
    os.dup2(devnull, 0)
    os.dup2(devnull, 1)
    os.dup2(devnull, 2)
    os.close(devnull)

    background_process(transcript_path, cwd, kg_path, project_name)


if __name__ == "__main__":
    main()
