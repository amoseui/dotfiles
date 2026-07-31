#!/usr/bin/env python3
"""Self-test for vault_lint.py and add_author.py using a tmp fixture vault."""
import json, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).parent

def run(script, *args):
    return subprocess.run([sys.executable, str(HERE / script), *args],
                          capture_output=True, text=True)

def main():
    with tempfile.TemporaryDirectory() as td:
        v = Path(td)
        (v / "sub").mkdir()
        (v / "a.md").write_text("links: [[b]] [[sub/c]] [[missing]] ![[img.png]]", encoding="utf-8")
        (v / "b.md").write_text("---\ntitle: b\n---\nbody [[a]]", encoding="utf-8")
        (v / "sub" / "c.md").write_text("no links", encoding="utf-8")

        # vault_lint: 3 md files, exactly 1 broken link ([[missing]])
        r = run("vault_lint.py", str(v))
        assert r.returncode == 0, r.stderr
        out = json.loads(r.stdout)
        assert out["md_count"] == 3, out
        assert out["broken_count"] == 1, out
        assert out["broken"][0]["target"] == "missing", out

        # add_author: adds to files without author, idempotent on rerun
        r = run("add_author.py", str(v), "claude")
        assert r.returncode == 0, r.stderr
        assert "changed=3 skipped=0" in r.stdout, r.stdout
        assert "author: claude" in (v / "b.md").read_text(encoding="utf-8")
        assert (v / "b.md").read_text(encoding="utf-8").count("---") == 2  # frontmatter intact
        r = run("add_author.py", str(v), "claude")
        assert "changed=0 skipped=3" in r.stdout, r.stdout
    print("ALL TESTS PASSED")

if __name__ == "__main__":
    main()
