#!/usr/bin/env python3
"""Vault integrity scan: .md count + broken wikilinks. Output: JSON to stdout."""
import json, re, sys
from pathlib import Path

WIKILINK = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
SKIP_PARTS = {".obsidian", ".trash"}
PROPOSAL_DIRS = ("6-agents/review",)

def scan(vault: Path) -> dict:
    md_files = [p for p in vault.rglob("*.md") if not SKIP_PARTS & set(p.parts)]
    stems = {p.stem for p in md_files}
    relpaths = {str(p.relative_to(vault).with_suffix("")) for p in md_files}
    broken = []
    for p in md_files:
        # Skip link scanning for APPLY-gated proposal directories
        rel_str = str(p.relative_to(vault)).replace("\\", "/")
        if any(rel_str.startswith(pd + "/") for pd in PROPOSAL_DIRS):
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        for m in WIKILINK.finditer(text):
            target = m.group(1).strip()
            if not target or "." in Path(target).name:  # embeds like img.png
                continue
            if target in stems or target in relpaths:
                continue
            broken.append({"file": str(p.relative_to(vault)), "target": target})
    return {"md_count": len(md_files), "broken_count": len(broken), "broken": broken}

if __name__ == "__main__":
    print(json.dumps(scan(Path(sys.argv[1]).expanduser()), ensure_ascii=False, indent=1))
