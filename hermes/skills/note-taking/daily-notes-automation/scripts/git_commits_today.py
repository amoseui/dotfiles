#!/usr/bin/env python3
"""오늘(KST) amoseui의 GitHub 커밋을 github.com/amoseui.atom 피드에서 추출.

gh 인증 불필요. atom <content>의 <blockquote>에 실제 커밋 메시지가 들어있다.
출력: 마크다운 bullet (`* repo: 커밋 메시지`), 없으면 `* 오늘 커밋 없음`.

사용:
  python3 git_commits_today.py            # 오늘(KST)
  python3 git_commits_today.py 2026-06-28 # 특정 날짜(KST)
"""
import sys, re, html, urllib.request
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))
USER = "amoseui"


def parse_dt(raw):
    # atom feed dates seen as "2026-06-28 12:57:01 UTC" or "... -0700"
    m = re.match(r"(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2}) (UTC|[+-]\d{4})", raw.strip())
    if not m:
        return None
    tz = timezone.utc if m.group(3) == "UTC" else datetime.strptime(m.group(3), "%z").tzinfo
    return datetime.fromisoformat(f"{m.group(1)}T{m.group(2)}").replace(tzinfo=tz)


def main():
    day = sys.argv[1] if len(sys.argv) > 1 else datetime.now(KST).strftime("%Y-%m-%d")
    url = f"https://github.com/{USER}.atom"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "hermes-daily-notes"})
        xml = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "replace")
    except Exception as e:
        print("* 오늘 커밋 없음 (피드 조회 실패: %s)" % e)
        return
    entries = re.findall(r"<entry>(.*?)</entry>", xml, re.S)
    out, seen = [], set()
    for e in entries:
        if "<id>tag:github.com,2008:push/" not in e:
            continue
        um = re.search(r"<updated>(.*?)</updated>", e)
        d = parse_dt(um.group(1)) if um else None
        if not d or d.astimezone(KST).strftime("%Y-%m-%d") != day:
            continue
        href = re.search(r'href="https://github.com/([\w.\-]+/[\w.\-]+)/(?:commit|compare|tree)', e)
        repo = href.group(1) if href else "?"
        cm = re.search(r"<content[^>]*>(.*?)</content>", e, re.S)
        if not cm:
            continue
        c = html.unescape(cm.group(1))
        for bq in re.findall(r"<blockquote>(.*?)</blockquote>", c, re.S):
            msg = re.sub(r"\s+", " ", re.sub(r"<.*?>", "", bq)).strip()
            # daily note 규칙: 대괄호 금지 → () 로 치환
            msg = msg.replace("[", "(").replace("]", ")")
            if not msg:
                continue
            key = (repo, msg)
            if key in seen:
                continue
            seen.add(key)
            out.append(f"* {repo}: {msg}")
    if out:
        print("\n".join(out))
    else:
        print("* 오늘 커밋 없음")


if __name__ == "__main__":
    main()
