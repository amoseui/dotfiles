#!/usr/bin/env python3
"""Add `author: <name>` to YAML frontmatter of every .md under <dir>. Idempotent."""
import re, sys
from pathlib import Path

def process(root: Path, author: str) -> tuple[int, int]:
    changed = skipped = 0
    for p in sorted(root.rglob("*.md")):
        text = p.read_text(encoding="utf-8")
        if text.startswith("---\n"):
            end = text.find("\n---\n", 4)
            if end == -1:  # malformed frontmatter -> treat as body
                new = f"---\nauthor: {author}\n---\n\n" + text
            else:
                fm = text[4:end]
                if re.search(r"^author:", fm, re.M):
                    skipped += 1
                    continue
                new = f"---\n{fm}\nauthor: {author}\n---\n" + text[end + 5:]
        else:
            new = f"---\nauthor: {author}\n---\n\n" + text
        p.write_text(new, encoding="utf-8")
        changed += 1
    return changed, skipped

if __name__ == "__main__":
    c, s = process(Path(sys.argv[1]).expanduser(), sys.argv[2])
    print(f"changed={c} skipped={s}")
