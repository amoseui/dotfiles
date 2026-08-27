#!/usr/bin/env python3
"""Deterministic tier-0 verification for dotfiles-sync.

Scans the staged diff (default) or the tracked tree (--tree) of the public
repo and the private submodule for:
  1. secrets      - case-insensitive key/value pairs (Bearer/cookie/private
                    key included), known token prefixes, private key blocks
                    (2026-08-24 Todoist incident class)
  2. third-party PII - roster-style "name id email" lines block; other
                    emails warn for human judgment (allow-list per address)
  3. placement    - personal-infra signals staged into the PUBLIC repo
  4. linker audit - link.sh `files` tuples the monthly-review parser cannot
                    see (multiline pairs, parseable pairs inside comments);
                    staged mode reads the index version, not the worktree

Secret values are never echoed back — reports mask everything after the
first four characters. Git/infra failures exit 2 (fail closed); BLOCK
findings exit 1; WARN-only runs exit 0. --self-test must pass before
trusting a modified copy of this script.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

SCANNER_PATH = "claude/skills/dotfiles-sync/scripts/precommit_scan.py"

SECRET_KEY = re.compile(
    r"(?i)\b(?:[a-z0-9_]*(?:token|secret|passwd|password|api[_-]?key|private[_-]?key|credential|authorization|cookie))\b\S*\s*[:=]\s*[\"']?(?!\$\{)(?:bearer\s+)?([A-Za-z0-9+/_.=-]{16,})"
)
KNOWN_PREFIX = re.compile(r"\b(?:ghp_|github_pat_|xox[bap]-|AIza[0-9A-Za-z_-]{20,}|ya29\.|glpat-|sk-(?:ant|proj|live)-)")
PRIVATE_KEY = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
ROSTER_LINE = re.compile(r"^\s*[^\s=:]+ [^\s=:]+ [A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\s*$")
TEMPLATE_VALUE = re.compile(r"^(?:YOUR_|REPLACE|CHANGE|<|x{4,})|_HERE\b", re.I)
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
EMAIL_ALLOW = re.compile(r"(?:git@github\.com|users\.noreply|^noreply@|@example\.com|@anthropic\.com|@openai\.com)")
PUBLIC_PERSONAL = re.compile(r"(?:Obsidian/amoseui|~/\.hermes|hermes/profiles/|\"chat_id\"|mentee-roster)")
PAIR = re.compile(r'\("([^"]+)", "([^"]+)"\)')


def mask(line: str, value: str) -> str:
    return line.strip().replace(value, value[:4] + "…(마스킹)")[:80]


def scan_line(path: str, lineno: int, line: str, public: bool, block: list, warn: list) -> None:
    m = SECRET_KEY.search(line)
    if m and not TEMPLATE_VALUE.search(m.group(1)):
        block.append(f"SECRET  {path}:{lineno}: {mask(line, m.group(1))}")
    if KNOWN_PREFIX.search(line):
        block.append(f"SECRET  {path}:{lineno}: known token prefix")
    if PRIVATE_KEY.search(line):
        block.append(f"SECRET  {path}:{lineno}: private key block")
    if ROSTER_LINE.match(line):
        block.append(f"PII     {path}:{lineno}: roster-style name/id/email line")
    else:
        for email in EMAIL.findall(line):
            if not EMAIL_ALLOW.search(email):
                warn.append(f"EMAIL   {path}:{lineno}: {email} — 본인 것인지, 커밋해도 되는지 확인")
    if public and PUBLIC_PERSONAL.search(line):
        warn.append(f"PLACE   {path}:{lineno}: public에 개인 인프라 신호 — private行이 아닌지 확인")


def run_git(repo: Path, *args: str) -> str:
    proc = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed in {repo}: {proc.stderr.strip()[:120]}")
    return proc.stdout


def scan_repo(repo: Path, public: bool, tree: bool, block: list, warn: list) -> None:
    if tree:
        for name in filter(None, run_git(repo, "ls-files").split("\n")):
            if public and name == SCANNER_PATH:
                continue
            try:
                text = (repo / name).read_text()
            except (UnicodeDecodeError, OSError):
                continue
            for i, line in enumerate(text.splitlines(), 1):
                scan_line(f"{repo.name}/{name}", i, line, public, block, warn)
    else:
        diff = run_git(repo, "diff", "--cached", "--unified=0")
        path = "?"
        for line in diff.splitlines():
            if line.startswith("+++ "):
                path = line[6:] if line.startswith("+++ b/") else "?"
            elif line.startswith("+"):
                if public and path == SCANNER_PATH:
                    continue
                scan_line(f"{repo.name}/{path}", 0, line[1:], public, block, warn)


def linker_content(repo: Path, rel: str, staged: bool) -> str | None:
    if staged:
        proc = subprocess.run(["git", "-C", str(repo), "show", f":{rel}"], capture_output=True, text=True)
        if proc.returncode == 0:
            return proc.stdout
    f = repo / rel
    return f.read_text() if f.is_file() else None


def check_linkers(repo: Path, staged: bool, block: list) -> None:
    # The public linker lives in the public index, the private one in the
    # submodule's own index — resolve each against its owning repository.
    for owner in (repo, repo / "private"):
        name = "link.sh"
        if not (owner / ".git").exists():
            continue
        text = linker_content(owner, name, staged)
        if text is None:
            continue
        m = re.search(r"files = \((.*?)\n\)", text, re.S)
        if not m:
            block.append(f"LINKER  {owner.name}/{name}: files 튜플을 찾지 못함 — 형식 변경 시 감사 스킬도 갱신")
            continue
        declared = parsed = 0
        for raw in m.group(1).splitlines():
            s = raw.strip()
            if s.startswith("#"):
                if PAIR.search(s):
                    block.append(f"LINKER  {owner.name}/{name}: 주석 안의 따옴표 쌍이 감사 파서에 오파싱됨: {s[:60]}")
                continue
            if '("' in s:
                declared += 1
            parsed += len(PAIR.findall(s))
        if declared != parsed:
            block.append(f"LINKER  {owner.name}/{name}: 선언 {declared}건 vs 한 줄 파싱 {parsed}건 — 멀티라인 매핑은 감사 사각")


def self_test() -> int:
    cases_block = [
        "      TODOIST_API_TOKEN: bc4a9823aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",  # 대문자 TOKEN + hex — 2026-08-24 사건
        "api_key = 'AbCdEf0123456789xyzw'",
        "ghp_0123456789abcdef0123456789abcdef0123",
        "홍길동 hong-gildong hong@synthetic-test.net",  # roster 형태 — 합성 데이터만 사용 (실존 인물 금지)
        "Authorization: Bearer abcdef0123456789opaquetoken",  # 2026-08-27 리뷰 P1 반영
        "cookie: sessionvalue0123456789abcd",
        "private_key: MIIEvAIBADANBgkqhkiG9w0BAQ",
    ]
    cases_pass = [
        "      TODOIST_API_TOKEN: ${TODOIST_API_TOKEN}",  # 플레이스홀더
        "  proactive_prune_tokens: 0",
        "git clone git@github.com:amoseui/dotfiles.git",
        "    email = amoseui@gmail.com",  # gitconfig 할당 줄 — roster 아님 (2026-08-27 오탐)
        '  api_key: "YOUR_TMDB_API_KEY_HERE"',  # 템플릿 플레이스홀더 (2026-08-27 오탐)
    ]
    failed = 0
    for line in cases_block:
        b, w = [], []
        scan_line("t", 1, line, False, b, w)
        if not b:
            print(f"SELF-TEST FAIL (미탐지): {line[:60]}")
            failed += 1
        for finding in b:
            if "SECRET" in finding and line.split()[-1][8:] in finding:
                print(f"SELF-TEST FAIL (값 노출): {finding[:70]}")
                failed += 1
    for line in cases_pass:
        b, w = [], []
        scan_line("t", 1, line, False, b, w)
        if b:
            print(f"SELF-TEST FAIL (오탐): {line[:60]} -> {b[0]}")
            failed += 1
    # allow-list는 주소별 적용 — 허용 주소가 같은 줄에 있어도 제3자 주소는 경고 (2026-08-27 리뷰 P2)
    b, w = [], []
    scan_line("t", 1, "cc: noreply@github.com and stranger@some-third-party.io", False, b, w)
    if not any("stranger@" in x for x in w):
        print("SELF-TEST FAIL: 줄 단위 allow-list가 제3자 이메일을 억제")
        failed += 1
    print("self-test:", "PASS" if failed == 0 else f"{failed} FAIL")
    return 1 if failed else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("repo", nargs="?", help="public dotfiles repo path")
    ap.add_argument("--tree", action="store_true", help="scan tracked trees instead of staged diffs")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    if not args.repo:
        ap.error("repo path required (or --self-test)")
    repo = Path(args.repo).expanduser().resolve()
    if not (repo / ".git").exists():
        print(f"ERROR: public repo가 아님(fail closed): {repo}")
        return 2
    block, warn = [], []
    try:
        scan_repo(repo, public=True, tree=args.tree, block=block, warn=warn)
        if (repo / "private" / ".git").exists():
            scan_repo(repo / "private", public=False, tree=args.tree, block=block, warn=warn)
        else:
            print("NOTE  private submodule 미초기화 — public만 검사")
        check_linkers(repo, staged=not args.tree, block=block)
    except RuntimeError as err:
        print(f"ERROR: {err} (fail closed)")
        return 2
    for w in warn:
        print("WARN ", w)
    for b in block:
        print("BLOCK", b)
    print(f"결과: BLOCK {len(block)}건 / WARN {len(warn)}건")
    return 1 if block else 0


if __name__ == "__main__":
    sys.exit(main())
