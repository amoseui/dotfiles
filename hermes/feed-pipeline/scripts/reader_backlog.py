#!/usr/bin/env python3
"""Readwise Reader: 안 읽은(location=new) 항목을 오래된 것부터 N개 가져온다.

토큰: ~/.hermes/.env 의 READWISE_TOKEN
출력: JSON 배열 [{id,title,author,site_name,url,source_url,category,created_at,published_date,reading_progress}]
정렬: created_at 오름차순(오래된 것 먼저). reading_progress>=0.95 (사실상 다 읽음)는 제외.

usage: reader_backlog.py [N]   (기본 30)
"""
import sys, json, pathlib, urllib.request, urllib.error

ENV = pathlib.Path.home() / ".hermes/.env"


def token():
    for line in ENV.read_text().splitlines():
        if line.startswith("READWISE_TOKEN="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("READWISE_TOKEN not in ~/.hermes/.env")


def fetch_all(tok, location="new"):
    """location의 모든 문서를 페이지네이션으로 수집."""
    out, cursor = [], None
    while True:
        url = "https://readwise.io/api/v3/list/?location=" + location
        if cursor:
            url += "&pageCursor=" + cursor
        req = urllib.request.Request(url, headers={"Authorization": "Token " + tok})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                d = json.load(r)
        except urllib.error.HTTPError as e:
            raise SystemExit("Readwise API error %s: %s" % (e.code, e.read()[:200]))
        out.extend(d.get("results", []))
        cursor = d.get("nextPageCursor")
        if not cursor:
            break
    return out


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    tok = token()
    docs = fetch_all(tok, "new")
    # 다 읽은 것 제외, 오래된 것부터 정렬
    docs = [d for d in docs if (d.get("reading_progress") or 0) < 0.95]
    docs.sort(key=lambda d: d.get("created_at") or "")
    picked = docs[:n]
    fields = ("id", "title", "author", "site_name", "url", "source_url",
              "category", "created_at", "published_date", "reading_progress")
    print(json.dumps([{k: d.get(k) for k in fields} for d in picked], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
