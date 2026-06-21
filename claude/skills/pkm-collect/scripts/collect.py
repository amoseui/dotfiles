#!/usr/bin/env python3
"""pkm-collect 수집기: Claude+Codex → digest.json(stdout). stdlib only.

SKILL.md이 config.yaml 값을 CLI 인자로 전달해 호출한다.
"""
from __future__ import annotations
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_digest
import codex_digest
import notes_index

DEFAULT_EXCLUDE_KEYWORDS = ["의료", "병원", "보험", "건강검진", "진료", "대장내시경"]


def resolve_since(marker_path, explicit_since):
    """since 결정: 명시값 > 마커 > 오늘 00:00(로컬)."""
    if explicit_since:
        return datetime.fromisoformat(explicit_since).astimezone()
    p = Path(marker_path)
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            return datetime.fromisoformat(data["last_run_ts"]).astimezone()
        except (ValueError, KeyError, json.JSONDecodeError):
            pass
    now = datetime.now().astimezone()
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def classify(digest, min_prompts, min_edits):
    """세션 기록가치 1차 분류(결정론)."""
    if digest["produced_pr"] or digest["commit_count"] or len(digest["edited_files"]) >= min_edits:
        return "substantial"
    if len(digest["user_prompts"]) >= min_prompts:
        return "borderline"
    return "trivial"


def is_sensitive(digest, keywords, paths):
    hay = " ".join(digest.get("user_prompts") or []) + " " + (digest.get("cwd") or "")
    if any(k and k in hay for k in keywords):
        return True
    cwd = digest.get("cwd") or ""
    return any(pp and pp in cwd for pp in paths)


def main(argv=None):
    ap = argparse.ArgumentParser(description="pkm-collect digest builder")
    ap.add_argument("--vault", required=True)
    # vault 기준 노트 인덱스 디렉터리(중복 감지용). 공백 포함 경로 허용(예: "5. Claude/notes").
    ap.add_argument("--note-dir", default="source/note")
    ap.add_argument("--claude-projects", default=str(Path.home() / ".claude/projects"))
    ap.add_argument("--codex-sessions", default=str(Path.home() / ".codex/sessions"))
    ap.add_argument("--codex-history", default=str(Path.home() / ".codex/history.jsonl"))
    ap.add_argument("--marker", default=str(Path(__file__).resolve().parent.parent / "state.json"))
    ap.add_argument("--since", default=None)
    ap.add_argument("--min-prompts", type=int, default=2)
    ap.add_argument("--min-edits", type=int, default=1)
    ap.add_argument("--prompt-truncate", type=int, default=400)
    ap.add_argument("--exclude-keywords", default=",".join(DEFAULT_EXCLUDE_KEYWORDS))
    ap.add_argument("--exclude-paths", default="")
    ap.add_argument("--include-subagents", action="store_true")
    ap.add_argument("--update-marker", default=None,
                    help="이 ISO 시각으로 마커 저장 후 종료")
    args = ap.parse_args(argv)

    # 마커 갱신 모드
    if args.update_marker:
        Path(args.marker).write_text(
            json.dumps({"last_run_ts": args.update_marker}, ensure_ascii=False, indent=2),
            encoding="utf-8")
        print(json.dumps({"updated_marker": args.update_marker}, ensure_ascii=False))
        return

    since = resolve_since(args.marker, args.since)
    since_epoch = since.timestamp()
    keywords = [k.strip() for k in args.exclude_keywords.split(",") if k.strip()]
    paths = [p.strip() for p in args.exclude_paths.split(",") if p.strip()]

    sessions = []
    proj_root = Path(args.claude_projects)
    if proj_root.exists():
        for jsonl in proj_root.rglob("*.jsonl"):
            if not args.include_subagents and "subagents" in jsonl.parts:
                continue
            try:
                if jsonl.stat().st_mtime < since_epoch:
                    continue
            except OSError:
                continue
            d = claude_digest.parse_claude_transcript(jsonl)
            if d:
                sessions.append(d)

    sessions.extend(codex_digest.build_codex_digests(
        args.codex_history, args.codex_sessions, since_epoch))

    kept = []
    for d in sessions:
        d["user_prompts"] = [p[:args.prompt_truncate] for p in d["user_prompts"]]
        if is_sensitive(d, keywords, paths):
            continue  # 민감 세션은 출력에서 완전 제외(LLM 비노출)
        d["triviality"] = classify(d, args.min_prompts, args.min_edits)
        if d["triviality"] == "trivial":
            continue
        kept.append(d)

    kept.sort(key=lambda x: x["started_at"])

    # 공백 포함 상대경로(예: "5. Claude/notes")를 안전하게 결합
    note_index_dir = Path(args.vault).joinpath(*Path(args.note_dir).parts)
    idx = notes_index.build_notes_index(note_index_dir)
    pr_urls = notes_index.pr_url_set(idx)
    for d in kept:
        d["already_documented"] = bool(d.get("pr_url") and d["pr_url"] in pr_urls)

    today = since.date().isoformat()
    idx_today = [e for e in idx if e.get("date") == today]

    print(json.dumps({
        "generated_at": datetime.now().astimezone().isoformat(),
        "since": since.isoformat(),
        "sessions": kept,
        "existing_notes_index": idx_today,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
