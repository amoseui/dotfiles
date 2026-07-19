#!/usr/bin/env python3
"""Aggregate Claude Code usage from transcripts + history.jsonl.

Outputs per-skill invocation counts (Skill tool + slash commands),
per-project activity, subagent usage, and monthly trends.
"""
import json
import glob
import os
import re
import collections
import datetime

HOME = os.path.expanduser("~")
PROJ = os.path.join(HOME, ".claude", "projects")
HISTORY = os.path.join(HOME, ".claude", "history.jsonl")

skill_counts = collections.Counter()          # skill -> count (Skill tool_use)
skill_last = {}                               # skill -> last date
skill_by_project = collections.defaultdict(collections.Counter)
cmd_counts = collections.Counter()            # <command-name> in transcripts
cmd_last = {}
agent_counts = collections.Counter()          # subagent_type -> count
project_sessions = collections.Counter()      # project -> session files
project_last = {}                             # project -> last activity date
monthly_skill = collections.defaultdict(collections.Counter)

CMD_RE = re.compile(r"<command-name>/?([\w:-]+)</command-name>")

for path in glob.glob(f"{PROJ}/*/*.jsonl"):
    project = os.path.basename(os.path.dirname(path))
    short = project.replace("-Users-amoseui-", "").replace("Workspace-github-", "")
    project_sessions[short] += 1
    mtime = datetime.date.fromtimestamp(os.path.getmtime(path)).isoformat()
    if project_last.get(short, "") < mtime:
        project_last[short] = mtime
    with open(path, errors="replace") as fh:
        for line in fh:
            ts = ""
            m = re.search(r'"timestamp":"(\d{4}-\d{2}-\d{2})', line)
            if m:
                ts = m.group(1)
            if '"type":"user"' in line and "<command-name>" in line:
                for cm in CMD_RE.findall(line):
                    cmd_counts[cm] += 1
                    if cmd_last.get(cm, "") < ts:
                        cmd_last[cm] = ts
            if '"type":"assistant"' not in line or '"tool_use"' not in line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            msg = obj.get("message") or {}
            date = (obj.get("timestamp") or "")[:10]
            month = date[:7]
            for c in msg.get("content") or []:
                if not isinstance(c, dict) or c.get("type") != "tool_use":
                    continue
                name = c.get("name") or ""
                inp = c.get("input") or {}
                if name == "Skill":
                    sk = inp.get("skill") or inp.get("command") or "?"
                    skill_counts[sk] += 1
                    skill_by_project[sk][short] += 1
                    monthly_skill[month][sk] += 1
                    if skill_last.get(sk, "") < date:
                        skill_last[sk] = date
                elif name in ("Task", "Agent"):
                    at = inp.get("subagent_type") or "general-purpose"
                    agent_counts[at] += 1

# --- history.jsonl: what the user actually types ---
slash_hist = collections.Counter()
slash_last = {}
kw_hist = collections.Counter()
kw_last = {}
hist_project = collections.Counter()
KEYWORDS = {
    "pkm collect": re.compile(r"pkm\s*collect|오늘 한 일 정리|일과 정리|하루 작업", re.I),
    "pkm push": re.compile(r"pkm\s*push", re.I),
    "pkm(노트/저널)": re.compile(r"\bpkm\b(?!\s*(collect|push))", re.I),
    "brief-morning": re.compile(r"아침 브리핑|모닝 브리핑|morning brief|업무 시작", re.I),
    "make-pr": re.compile(r"PR 만들|PR 생성|PR 올려|make.?pr", re.I),
    "handoff": re.compile(r"handoff|인수인계|핸드오프", re.I),
    "dotfiles-sync": re.compile(r"dotfiles에|dotfiles 반영|dotfiles 업데이트|설정 백업", re.I),
    "review-claudemd": re.compile(r"claudemd|CLAUDE\.md 점검|지침 점검", re.I),
    "workspace-flow": re.compile(r"workspace.?flow|워크스페이스 플로우|정식 절차", re.I),
    "monthly-review": re.compile(r"monthly.?review|월간 점검|인프라 점검|infra review", re.I),
}
if os.path.exists(HISTORY):
    with open(HISTORY, errors="replace") as fh:
        for line in fh:
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            disp = (obj.get("display") or "").strip()
            ts = obj.get("timestamp") or 0
            date = datetime.date.fromtimestamp(ts / 1000).isoformat() if ts else ""
            proj = (obj.get("project") or "").replace(f"{HOME}/", "")
            hist_project[proj] += 1
            if disp.startswith("/"):
                cmd = disp.split()[0].lstrip("/")
                slash_hist[cmd] += 1
                if slash_last.get(cmd, "") < date:
                    slash_last[cmd] = date
            for label, rx in KEYWORDS.items():
                if rx.search(disp):
                    kw_hist[label] += 1
                    if kw_last.get(label, "") < date:
                        kw_last[label] = date

def dump(title, counter, last=None, limit=40):
    print(f"\n## {title}")
    for k, v in counter.most_common(limit):
        tail = f"  (last: {last.get(k, '?')})" if last else ""
        print(f"  {v:4d}  {k}{tail}")

dump("Skill tool invocations (transcripts, all time)", skill_counts, skill_last)
dump("Slash commands in transcripts (<command-name>)", cmd_counts, cmd_last)
dump("Slash commands typed (history.jsonl)", slash_hist, slash_last)
dump("Keyword triggers typed (history.jsonl)", kw_hist, kw_last)
dump("Subagent usage (Task/Agent)", agent_counts)
dump("Sessions per project", project_sessions, project_last)
dump("Prompts typed per project (history)", hist_project, limit=20)

print("\n## Monthly skill trend (top skills)")
for month in sorted(monthly_skill):
    tops = ", ".join(f"{k}×{v}" for k, v in monthly_skill[month].most_common(8))
    print(f"  {month}: {tops}")

print("\n## Per-skill project spread (custom skills only)")
SKILLS_DIR = os.path.join(HOME, ".claude", "skills")
CUSTOM = sorted(d for d in os.listdir(SKILLS_DIR)
                if os.path.isdir(os.path.join(SKILLS_DIR, d)))
for sk in CUSTOM:
    if sk in skill_by_project:
        spread = ", ".join(f"{p}×{n}" for p, n in skill_by_project[sk].most_common(5))
        print(f"  {sk}: {spread}")
