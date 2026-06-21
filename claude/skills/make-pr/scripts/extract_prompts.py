#!/usr/bin/env python3
"""
Claude Code 세션 로그에서 사용자 프롬프트를 추출하는 스크립트.

사용법:
  python extract_prompts.py <jsonl_path>
  python extract_prompts.py <jsonl_path> --pretty
  python extract_prompts.py --find-latest <project_dir>
"""

import json
import sys
import os
import re
import argparse
from datetime import datetime
from pathlib import Path




# 무의미한 단답 응답 목록
TRIVIAL_RESPONSES = frozenset({
    "/clear", "/help", "/exit",
    "y", "n", "네", "아니", "ok", "yes", "no",
    "계속", "ㅇ", "ㅇㅇ",
})

# 제외할 접두사 패턴
EXCLUDED_PREFIXES = (
    "<command-name>",
    "<local-command-caveat>",
    "<local-command-stdout>",
    "<local-command-stderr>",
    "<teammate-message",
)

# 이 태그가 content 내에 포함되면 제외 (위치 무관)
EXCLUDED_SUBSTRINGS = (
    "<persisted-output>",
)

# 스킬 이름 추출 정규식
SKILL_NAME_RE = re.compile(r"<command-name>(.*?)</command-name>")

# 민감 정보 마스킹 패턴 (패턴, 치환 문자열)
SENSITIVE_PATTERNS = [
    # Anthropic / OpenAI API 키
    (re.compile(r'\bsk-[a-zA-Z0-9\-_]{20,}'), "sk-***"),
    # Slack 봇/사용자 토큰
    (re.compile(r'\bxox[bpoas]-[a-zA-Z0-9\-]+'), "xox*-***"),
    # Authorization: Bearer 헤더
    (re.compile(r'(?i)(bearer\s+)[a-zA-Z0-9\-_.~+/]+=*'), r"\1***"),
    # key=, token=, secret=, password= 뒤의 값
    (re.compile(r'(?i)(\b(?:api[-_]?key|token|secret|password|auth[-_]?token)\s*[:=]\s*)[^\s,\'"&\n]{6,}'), r"\1***"),
]


def mask_sensitive(text):
    """프롬프트 텍스트에서 민감 정보를 마스킹한다."""
    for pattern, replacement in SENSITIVE_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def _get_claude_projects_dir(project_dir):
    """프로젝트 디렉토리를 ~/.claude/projects/<key>/ 경로로 변환한다."""
    project_dir = os.path.abspath(project_dir)
    dir_name = project_dir.replace("/", "-")
    return Path.home() / ".claude" / "projects" / dir_name


def find_latest_session(project_dir):
    """
    ~/.claude/projects/ 하위에서 현재 프로젝트의 최신 세션 .jsonl 파일을 찾는다.

    project_dir: 절대 경로 (예: /Users/casper/Workspace/akira-bot)
    반환: 최신 .jsonl 파일 경로 또는 None
    """
    claude_projects_dir = _get_claude_projects_dir(project_dir)
    if not claude_projects_dir.is_dir():
        return None

    jsonl_files = list(claude_projects_dir.glob("*.jsonl"))
    if not jsonl_files:
        return None

    latest = max(jsonl_files, key=lambda f: f.stat().st_mtime)
    return str(latest)


def find_sessions_since(project_dir, since_ts):
    """
    지정한 타임스탬프 이후에 수정된 .jsonl 파일을 mtime 오름차순으로 반환한다.

    project_dir: 절대 경로
    since_ts: ISO 8601 문자열 (예: "2025-03-10T09:00:00+09:00")
    반환: 파일 경로 문자열 리스트 (오래된 순)
    """
    claude_projects_dir = _get_claude_projects_dir(project_dir)
    if not claude_projects_dir.is_dir():
        return []

    # ISO 8601 → Unix timestamp 변환
    try:
        ts_str = since_ts.replace("Z", "+00:00")
        since_dt = datetime.fromisoformat(ts_str)
        since_unix = since_dt.timestamp()
    except (ValueError, TypeError):
        print(
            "경고: --since 파싱 실패 ({}), 모든 세션 파일 사용".format(since_ts),
            file=sys.stderr,
        )
        since_unix = 0.0

    jsonl_files = [
        f for f in claude_projects_dir.glob("*.jsonl")
        if f.stat().st_mtime >= since_unix
    ]

    if not jsonl_files:
        return []

    # 오래된 순(mtime 오름차순)으로 정렬 → 시간 순서대로 프롬프트를 합친다
    jsonl_files.sort(key=lambda f: f.stat().st_mtime)
    return [str(f) for f in jsonl_files]


def merge_records(paths):
    """
    여러 .jsonl 파일의 레코드를 시간순으로 합치고 uuid 중복을 제거한다.

    반환: 중복 제거된 레코드 리스트 (timestamp 오름차순)
    """
    seen_uuids = set()
    all_records = []

    for path in paths:
        for record in parse_records(path):
            uid = record.get("uuid")
            if uid and uid in seen_uuids:
                continue
            if uid:
                seen_uuids.add(uid)
            all_records.append(record)

    # timestamp 기준 오름차순 정렬 (없는 레코드는 마지막으로)
    all_records.sort(key=lambda r: r.get("timestamp") or "")
    return all_records


def parse_records(jsonl_path):
    """JSONL 파일을 파싱하여 레코드 목록을 반환한다."""
    records = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                records.append(record)
            except json.JSONDecodeError as e:
                print(
                    "경고: {}번째 줄 파싱 실패 - {}".format(line_num, e),
                    file=sys.stderr,
                )
    return records


def build_parent_uuid_index(records):
    """parentUuid → assistant record 딕셔너리를 구축한다. (O(1) 응답 조회용)"""
    index = {}
    for record in records:
        if record.get("type") == "assistant":
            parent = record.get("parentUuid")
            if parent:
                index[parent] = record
    return index


def find_assistant_response(prompt_uuid, parent_uuid_index):
    """
    parentUuid 인덱스를 통해 O(1)으로 assistant 응답을 찾아
    tools_used와 text_preview를 반환한다.
    """
    record = parent_uuid_index.get(prompt_uuid)
    if not record:
        return None

    content = record.get("message", {}).get("content", [])
    if isinstance(content, str):
        preview = content[:200] if content else ""
        return {"tools_used": [], "text_preview": preview}

    if not isinstance(content, list):
        return None

    tools_used = []
    text_preview = ""
    for item in content:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "tool_use":
            name = item.get("name", "")
            if name:
                tools_used.append(name)
        elif item.get("type") == "text" and not text_preview:
            text_preview = item.get("text", "")[:200]

    return {"tools_used": tools_used, "text_preview": text_preview}


def is_user_answer_record(record):
    """
    AskUserQuestion 응답 레코드인지 확인한다.
    type="user", isMeta=false, content가 list이고
    tool_result에 "User has answered" 패턴이 포함된 경우.
    """
    if record.get("type") != "user":
        return False
    if record.get("isMeta", False):
        return False

    content = record.get("message", {}).get("content")
    if not isinstance(content, list):
        return False

    for item in content:
        if not isinstance(item, dict):
            continue
        if item.get("type") != "tool_result":
            continue
        result_content = item.get("content", "")
        if isinstance(result_content, str) and result_content.startswith("User has answered"):
            return True

    return False


def extract_user_answer_text(record):
    """AskUserQuestion 응답 레코드에서 사용자 답변 텍스트를 추출한다."""
    content = record.get("message", {}).get("content", [])
    for item in content:
        if not isinstance(item, dict):
            continue
        if item.get("type") != "tool_result":
            continue
        result_content = item.get("content", "")
        if isinstance(result_content, str) and result_content.startswith("User has answered"):
            return result_content
    return ""


def extract_prompts(records):
    """
    레코드 목록에서 유의미한 프롬프트, 스킬 호출, AskUserQuestion 응답을 추출한다.
    """
    parent_uuid_index = build_parent_uuid_index(records)

    prompts = []
    skill_invocations = []
    timestamps = []

    for record in records:
        # 타임스탬프 수집 (통계용)
        ts = record.get("timestamp")
        if ts:
            timestamps.append(ts)

        # AskUserQuestion 응답 추출
        if is_user_answer_record(record):
            answer_text = extract_user_answer_text(record)
            prompt_uuid = record.get("uuid", "")
            prompt_entry = {
                "uuid": prompt_uuid,
                "timestamp": record.get("timestamp", ""),
                "content": answer_text,
                "length": len(answer_text),
                "is_user_answer": True,
            }
            # 응답 추적
            response = find_assistant_response(prompt_uuid, parent_uuid_index)
            if response:
                prompt_entry["agent_response"] = response
            prompts.append(prompt_entry)
            continue

        # user 타입이 아니면 건너뛰기
        if record.get("type") != "user":
            continue

        # 메타 메시지 제외
        if record.get("isMeta", False):
            continue

        message = record.get("message", {})
        content = message.get("content")

        # content가 str이 아니면 제외 (list이면 tool_result)
        if not isinstance(content, str):
            continue

        # 스킬 호출 확인 (command-name 태그 포함)
        skill_match = SKILL_NAME_RE.search(content)
        if skill_match:
            skill_invocations.append({
                "uuid": record.get("uuid", ""),
                "timestamp": record.get("timestamp", ""),
                "skill_name": skill_match.group(1),
                "raw_content": content,
            })
            continue

        # 제외할 접두사로 시작하는 메시지 건너뛰기
        if content.startswith(EXCLUDED_PREFIXES):
            continue

        # 제외할 부분 문자열을 포함하는 메시지 건너뛰기
        if any(sub in content for sub in EXCLUDED_SUBSTRINGS):
            continue

        # 길이 필터
        if len(content) < 10:
            continue

        # 무의미한 단답 응답 제외
        content_stripped = content.strip().lower()
        if content_stripped in TRIVIAL_RESPONSES:
            continue

        prompt_uuid = record.get("uuid", "")
        content = mask_sensitive(content)
        prompt_entry = {
            "uuid": prompt_uuid,
            "timestamp": record.get("timestamp", ""),
            "content": content,
            "length": len(content),
        }

        # 응답 추적
        response = find_assistant_response(prompt_uuid, parent_uuid_index)
        if response:
            prompt_entry["agent_response"] = response

        prompts.append(prompt_entry)

    # 통계 계산
    stats = _compute_stats(prompts, skill_invocations, timestamps, records)

    return {
        "prompts": prompts,
        "skill_invocations": skill_invocations,
        "stats": stats,
    }


def _compute_stats(prompts, skill_invocations, timestamps, records):
    """추출 결과 통계를 계산한다."""
    # 전체 user 메시지 수 (isMeta 제외)
    total_count = 0
    for r in records:
        if r.get("type") == "user" and not r.get("isMeta", False):
            total_count += 1

    meaningful_count = len(prompts)
    skill_invocations_count = len(skill_invocations)

    # 평균 길이
    if meaningful_count > 0:
        avg_length = sum(p["length"] for p in prompts) // meaningful_count
    else:
        avg_length = 0

    # 세션 시간 범위
    session_start = ""
    session_end = ""
    duration_minutes = 0

    if timestamps:
        sorted_ts = sorted(timestamps)
        session_start = sorted_ts[0]
        session_end = sorted_ts[-1]

        try:
            # ISO 8601 파싱 (Z 접미사 처리)
            start_str = session_start.replace("Z", "+00:00")
            end_str = session_end.replace("Z", "+00:00")

            # Python 3.8 호환: fromisoformat이 Z를 처리하지 못함
            start_dt = datetime.fromisoformat(start_str)
            end_dt = datetime.fromisoformat(end_str)
            delta = end_dt - start_dt
            duration_minutes = int(delta.total_seconds() / 60)
        except (ValueError, TypeError):
            duration_minutes = 0

    return {
        "total_count": total_count,
        "meaningful_count": meaningful_count,
        "skill_invocations_count": skill_invocations_count,
        "avg_length": avg_length,
        "session_start": session_start,
        "session_end": session_end,
        "duration_minutes": duration_minutes,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Claude Code 세션 로그에서 사용자 프롬프트를 추출한다.",
    )
    parser.add_argument(
        "jsonl_paths",
        nargs="*",
        help="세션 로그 .jsonl 파일 경로 (여러 개 지정 가능)",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="JSON 출력을 보기 좋게 포맷팅",
    )
    parser.add_argument(
        "--find-latest",
        metavar="PROJECT_DIR",
        help="프로젝트 디렉토리의 최신 세션 로그 하나를 자동으로 찾아 사용",
    )
    parser.add_argument(
        "--find-since",
        metavar="PROJECT_DIR",
        help="--since 이후에 수정된 세션 로그를 모두 찾아 사용 (--since 필수)",
    )
    parser.add_argument(
        "--since",
        metavar="ISO_TIMESTAMP",
        help="이 타임스탬프 이후 수정된 세션 파일만 포함 (--find-since와 함께 사용)",
    )

    args = parser.parse_args()

    # 파일 목록 결정
    paths = list(args.jsonl_paths)

    if args.find_since:
        since_ts = args.since or ""
        found = find_sessions_since(args.find_since, since_ts)
        if not found:
            print(
                "경고: '{}' 프로젝트에서 {} 이후 세션 로그를 찾을 수 없습니다.".format(
                    args.find_since, since_ts or "모든 시간",
                ),
                file=sys.stderr,
            )
        else:
            print(
                "세션 로그 {}개 발견: {}".format(len(found), ", ".join(found)),
                file=sys.stderr,
            )
            paths.extend(found)

    elif args.find_latest:
        found_path = find_latest_session(args.find_latest)
        if not found_path:
            print(
                "오류: '{}' 프로젝트의 세션 로그를 찾을 수 없습니다.".format(
                    args.find_latest,
                ),
                file=sys.stderr,
            )
            sys.exit(1)
        print("세션 로그 발견: {}".format(found_path), file=sys.stderr)
        paths.append(found_path)

    if not paths:
        parser.print_help()
        sys.exit(1)

    # 존재하지 않는 파일 필터링
    valid_paths = []
    for p in paths:
        if os.path.isfile(p):
            valid_paths.append(p)
        else:
            print("경고: 파일을 찾을 수 없어 건너뜁니다 - {}".format(p), file=sys.stderr)

    if not valid_paths:
        print("오류: 유효한 파일이 없습니다.", file=sys.stderr)
        sys.exit(1)

    # 레코드 합치기 (여러 파일이면 merge, 단일 파일이면 그냥 파싱)
    if len(valid_paths) == 1:
        records = parse_records(valid_paths[0])
    else:
        records = merge_records(valid_paths)

    if not records:
        print("오류: 파싱된 레코드가 없습니다.", file=sys.stderr)
        sys.exit(1)

    # 프롬프트 추출
    result = extract_prompts(records)

    # JSON 출력
    indent = 2 if args.pretty else None
    print(json.dumps(result, ensure_ascii=False, indent=indent))


if __name__ == "__main__":
    main()
