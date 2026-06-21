#!/usr/bin/env python3
"""source/note frontmatter 인덱스(중복 감지용). stdlib only."""
from __future__ import annotations
from pathlib import Path


def _read_frontmatter(path):
    """파일 앞 --- ... --- 블록을 top-level key:value dict로 파싱(들여쓰기/리스트 무시)."""
    fm = {}
    try:
        with Path(path).open(encoding="utf-8") as fh:
            if fh.readline().strip() != "---":
                return fm
            for line in fh:
                if line.strip() == "---":
                    break
                if ":" in line and not line[:1].isspace() and not line.startswith("-"):
                    key, _, val = line.partition(":")
                    fm[key.strip()] = val.strip()
    except OSError:
        pass
    return fm


def build_notes_index(note_dir):
    """note_dir/*.md → [{file, title, pr_url, repository, date}]."""
    out = []
    base = Path(note_dir)
    if not base.exists():
        return out
    for path in sorted(base.glob("*.md")):
        fm = _read_frontmatter(path)
        out.append({
            "file": str(path),
            "title": path.stem,
            "pr_url": fm.get("pr_url"),
            "repository": fm.get("repository"),
            "date": fm.get("date"),
        })
    return out


def pr_url_set(index):
    return {e["pr_url"] for e in index if e.get("pr_url")}
