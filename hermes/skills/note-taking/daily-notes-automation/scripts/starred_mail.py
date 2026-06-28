#!/usr/bin/env python3
"""두 Google 계정(amoseui, prenine)의 별표편지함 메일을 모두 합쳐 한 줄 요약.

각 계정의 토큰은 HERMES_HOME 격리 폴더에 분리 저장돼 있다:
  ~/.hermes/google-accounts/amoseui/google_token.json
  ~/.hermes/google-accounts/prenine/google_token.json

google_api.py를 HERMES_HOME 환경변수만 바꿔가며 호출해 계정을 전환한다.
출력: `* [발신자] 제목` bullet (별표 전체, 날짜 필터 없음), 없으면 `* 새로운 중요 메일 없음`.
대괄호 [ ]를 피하기 위해 발신자는 () 안에 넣는다.
"""
import os, sys, json, subprocess
from pathlib import Path

HOME = Path.home()
GAPI = HOME / ".hermes/skills/productivity/google-workspace/scripts/google_api.py"
ACCOUNTS = {
    "amoseui": HOME / ".hermes/google-accounts/amoseui",
    "prenine": HOME / ".hermes/google-accounts/prenine",
}
MAX = 25  # 계정당 최대


def fetch(account, hermes_home):
    env = dict(os.environ, HERMES_HOME=str(hermes_home))
    r = subprocess.run(
        [sys.executable, str(GAPI), "gmail", "search", "is:starred", "--max", str(MAX)],
        env=env, capture_output=True, text=True, timeout=90,
    )
    out = r.stdout.strip()
    try:
        return json.loads(out)
    except Exception:
        return []  # "No messages found." 등


def clean(s):
    return (s or "").replace("[", "(").replace("]", ")").strip()


def main():
    lines, seen = [], set()
    for acct, home in ACCOUNTS.items():
        if not (home / "google_token.json").exists():
            continue
        for m in fetch(acct, home):
            frm = clean(m.get("from", "").split("<")[0].strip().strip('"'))
            subj = clean(m.get("subject", ""))
            key = (frm, subj)
            if key in seen:
                continue
            seen.add(key)
            tag = "" if acct == "amoseui" else f" ({acct})"
            lines.append(f"* ({frm}) {subj}{tag}")
    if lines:
        print("\n".join(lines))
    else:
        print("* 새로운 중요 메일 없음")


if __name__ == "__main__":
    main()
