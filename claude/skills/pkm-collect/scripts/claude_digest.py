#!/usr/bin/env python3
"""Claude Code 트랜스크립트(JSONL) → 세션 다이제스트. stdlib only, 순수 함수."""
from __future__ import annotations
import json
import re
from datetime import datetime
from pathlib import Path

# 실제 유저 프롬프트가 아닌 노이즈 프리픽스(슬래시 커맨드/캐비엇)
_NOISE_PREFIXES = (
    "<local-command-caveat>", "<command-name>", "<command-message>",
    "<command-args>", "Caveat:",
)
_PR_URL_RE = re.compile(r"https?://[^\s)\"']+/pull/\d+")
_GIT_COMMIT_RE = re.compile(r"\bgit\s+commit\b")
_GH_PR_CREATE_RE = re.compile(r"\bgh\s+pr\s+create\b")


def _parse_ts(value):
    """ISO8601(...Z) → 로컬 타임존 aware datetime (실패 시 None)."""
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
    return dt.astimezone()


def parse_claude_transcript(path):
    """트랜스크립트 1개 파싱 → 세션 다이제스트 dict. 타임스탬프 없으면 None."""
    path = Path(path)
    user_prompts, edited_files, skills_used, branches = [], set(), set(), set()
    tool_counts, timestamps = {}, []
    commit_count, produced_pr, pr_url, cwd, session_id = 0, False, None, None, None

    with path.open(encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                rec = json.loads(raw)
            except json.JSONDecodeError:
                continue

            if rec.get("timestamp"):
                dt = _parse_ts(rec["timestamp"])
                if dt:
                    timestamps.append(dt)
            if rec.get("cwd"):
                cwd = rec["cwd"]
            if rec.get("gitBranch"):
                branches.add(rec["gitBranch"])
            if rec.get("sessionId"):
                session_id = rec["sessionId"]

            typ = rec.get("type")
            msg = rec.get("message") or {}
            content = msg.get("content")

            if typ == "user" and rec.get("userType") == "external":
                if isinstance(content, str):
                    text = content.strip()
                    if text and not text.startswith(_NOISE_PREFIXES):
                        user_prompts.append(text)
                elif isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_result":
                            inner = block.get("content")
                            txt = inner if isinstance(inner, str) else json.dumps(inner, ensure_ascii=False)
                            m = _PR_URL_RE.search(txt)
                            # PR URL은 이 세션이 실제로 PR을 생성한 경우(gh pr create/make-pr → produced_pr=True)에만 채택.
                            # 트랜스크립트에 PR 링크가 출력·언급만 된 경우(리뷰 등)를 PR 생성으로 오인하지 않는다.
                            if m and not pr_url and produced_pr:
                                pr_url = m.group(0)

            elif typ == "assistant" and isinstance(content, list):
                for block in content:
                    if not isinstance(block, dict) or block.get("type") != "tool_use":
                        continue
                    name = block.get("name", "")
                    tool_counts[name] = tool_counts.get(name, 0) + 1
                    inp = block.get("input") or {}
                    if name in ("Edit", "Write", "NotebookEdit"):
                        fp = inp.get("file_path") or inp.get("notebook_path")
                        if fp:
                            edited_files.add(fp)
                    elif name == "Bash":
                        cmd = str(inp.get("command", ""))
                        if _GIT_COMMIT_RE.search(cmd):
                            commit_count += 1
                        if _GH_PR_CREATE_RE.search(cmd):
                            produced_pr = True
                    elif name == "Skill":
                        sk = str(inp.get("skill") or inp.get("command") or "")
                        if sk:
                            skills_used.add(sk)
                            if "make-pr" in sk:
                                produced_pr = True

    if not timestamps:
        return None
    started, ended = min(timestamps), max(timestamps)
    return {
        "source": "claude",
        "session_id": session_id or path.stem,
        "cwd": cwd,
        "project": Path(cwd).name if cwd else "unknown",
        "branches": sorted(branches),
        "started_at": started.isoformat(),
        "ended_at": ended.isoformat(),
        "duration_min": round((ended - started).total_seconds() / 60, 1),
        "user_prompts": user_prompts,
        "edited_files": sorted(edited_files),
        "commit_count": commit_count,
        "produced_pr": produced_pr,
        "pr_url": pr_url,
        "skills_used": sorted(skills_used),
        "tool_counts": tool_counts,
        "transcript_path": str(path),
    }
