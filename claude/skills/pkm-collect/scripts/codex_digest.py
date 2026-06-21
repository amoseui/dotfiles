#!/usr/bin/env python3
"""Codex CLI 세션 → 세션 다이제스트. history.jsonl(프롬프트) + rollout 정규식 스캔(신호)."""
from __future__ import annotations
import json
import re
from datetime import datetime
from pathlib import Path

_PR_URL_RE = re.compile(r"https?://[^\s)\"']+/pull/\d+")
_GH_PR_CREATE_RE = re.compile(r"gh\s+pr\s+create")
_PATCH_FILE_RE = re.compile(r"\*\*\* (?:Add|Update|Delete) File: ([^\\']+)")
_CWD_RE = re.compile(r'"cwd"\s*:\s*"([^"]+)"')


def load_codex_history(history_path, since_epoch):
    """history.jsonl → {session_id: {prompts, min_ts, max_ts}} (since_epoch 이후만)."""
    sessions = {}
    p = Path(history_path)
    if not p.exists():
        return sessions
    with p.open(encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                rec = json.loads(raw)
            except json.JSONDecodeError:
                continue
            sid, ts, text = rec.get("session_id"), rec.get("ts"), rec.get("text")
            if not sid or ts is None or ts < since_epoch:
                continue
            s = sessions.setdefault(sid, {"prompts": [], "min_ts": ts, "max_ts": ts})
            if text:
                s["prompts"].append(text)
            s["min_ts"], s["max_ts"] = min(s["min_ts"], ts), max(s["max_ts"], ts)
    return sessions


def _find_rollout(sessions_dir, session_id):
    base = Path(sessions_dir)
    if not base.exists():
        return None
    for path in base.rglob("*" + session_id + "*.jsonl"):
        return path
    return None


def _scan_rollout(path):
    """rollout 원본 정규식 스캔 → 작업 신호(포맷 비의존)."""
    text = Path(path).read_text(encoding="utf-8", errors="ignore")
    edited = sorted({m.group(1).strip() for m in _PATCH_FILE_RE.finditer(text)})
    pr_url = None
    produced_pr = bool(_GH_PR_CREATE_RE.search(text))
    m = _PR_URL_RE.search(text)
    if m:
        pr_url, produced_pr = m.group(0), True
    cwd_m = _CWD_RE.search(text)
    return {"edited_files": edited, "produced_pr": produced_pr,
            "pr_url": pr_url, "cwd": cwd_m.group(1) if cwd_m else None}


def build_codex_digests(history_path, sessions_dir, since_epoch):
    out = []
    for sid, info in load_codex_history(history_path, since_epoch).items():
        started = datetime.fromtimestamp(info["min_ts"]).astimezone()
        ended = datetime.fromtimestamp(info["max_ts"]).astimezone()
        d = {
            "source": "codex", "session_id": sid, "cwd": None, "project": "unknown",
            "branches": [], "started_at": started.isoformat(), "ended_at": ended.isoformat(),
            "duration_min": round((ended - started).total_seconds() / 60, 1),
            "user_prompts": info["prompts"], "edited_files": [], "commit_count": 0,
            "produced_pr": False, "pr_url": None, "skills_used": [], "tool_counts": {},
            "transcript_path": None,
        }
        rollout = _find_rollout(sessions_dir, sid)
        if rollout:
            sig = _scan_rollout(rollout)
            d["edited_files"] = sig["edited_files"]
            d["produced_pr"] = sig["produced_pr"]
            d["pr_url"] = sig["pr_url"]
            d["transcript_path"] = str(rollout)
            if sig["cwd"]:
                d["cwd"], d["project"] = sig["cwd"], Path(sig["cwd"]).name
        out.append(d)
    return out
