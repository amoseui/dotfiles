#!/usr/bin/env python3
"""URL의 본문 텍스트 + 본문 안 세부 링크(1-hop)를 추출한다. RSS 리더처럼 '실제로 읽기'.

여러 URL을 받아 병렬로 fetch:
- 본문: <article>/<main> 우선, 없으면 <body>에서 script/style/nav 제거 후 텍스트화
- 본문 내 링크: 의미 있는 외부/내부 링크만 (트래킹·SNS·구독취소·mailto·앵커 제외)

입력: stdin JSON 배열 [{...,"source_url"|"link"|"url": "..."}]  또는 인자로 URL 나열
출력: 같은 객체에 body_excerpt(최대 ~1500자), inner_links[{text,href}] (상위 25개) 추가

usage:
  echo '[{"source_url":"https://..."}]' | python3 fetch_content.py
  python3 fetch_content.py https://a.com https://b.com
"""
import sys, json, re, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

UA = "Mozilla/5.0 (feed-pipeline; reader)"
MAX_BODY = 1500
MAX_LINKS = 25

# 제외할 링크 패턴 (트래킹/소셜/구독관리/공유 등)
SKIP_LINK = re.compile(
    r"(unsubscribe|구독취소|수신거부|mailto:|javascript:|"
    r"facebook\.com|twitter\.com|x\.com/|instagram\.com|linkedin\.com/share|"
    r"t\.me/|pinterest\.|youtube\.com/(?!watch)|/share|utm_|/feed|\.rss|"
    r"list-manage|mailchi\.mp|stibee\.com/.*?/unsubscribe)",
    re.I,
)
SKIP_TEXT = re.compile(r"^(공유|share|tweet|구독|subscribe|더보기|read more|\s*)$", re.I)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=25) as r:
        raw = r.read()
        enc = r.headers.get_content_charset() or "utf-8"
        return raw.decode(enc, errors="replace"), r.geturl()


def main_region(html):
    """본문 영역 추출: article > main > body."""
    for tag in ("article", "main"):
        m = re.search(r"<%s\b[^>]*>(.*?)</%s>" % (tag, tag), html, re.S | re.I)
        if m:
            return m.group(1)
    m = re.search(r"<body\b[^>]*>(.*?)</body>", html, re.S | re.I)
    return m.group(1) if m else html


def clean_text(region):
    t = re.sub(r"<(script|style|nav|header|footer|aside|form)\b.*?</\1>", " ", region, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"&nbsp;", " ", t)
    t = re.sub(r"&amp;", "&", t)
    t = re.sub(r"&lt;", "<", t).replace("&gt;", ">").replace("&#39;", "'").replace("&quot;", '"')
    t = re.sub(r"[ \t\u200b\u00ad\u034f]+", " ", t)
    t = re.sub(r"\n\s*\n+", "\n\n", t)
    return t.strip()


def extract_links(region, base):
    out, seen = [], set()
    for m in re.finditer(r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>', region, re.S | re.I):
        href, text = m.group(1).strip(), clean_text(m.group(2))
        if not href or href.startswith("#"):
            continue
        href = urllib.parse.urljoin(base, href)
        if SKIP_LINK.search(href) or SKIP_TEXT.match(text or ""):
            continue
        if len(text) < 4:  # 텍스트 너무 짧은 링크(아이콘 등) 제외
            continue
        if href in seen:
            continue
        seen.add(href)
        out.append({"text": text[:120], "href": href})
        if len(out) >= MAX_LINKS:
            break
    return out


def process(item):
    url = item.get("source_url") or item.get("link") or item.get("url")
    if not url:
        item["fetch_error"] = "no url"
        return item
    try:
        html, final = fetch(url)
    except Exception as e:
        item["fetch_error"] = "%s" % e
        return item
    region = main_region(html)
    body = clean_text(region)
    item["body_excerpt"] = body[:MAX_BODY]
    item["inner_links"] = extract_links(region, final)
    item["fetched_url"] = final
    return item


def main():
    if not sys.stdin.isatty() and len(sys.argv) == 1:
        items = json.load(sys.stdin)
    else:
        items = [{"source_url": u} for u in sys.argv[1:]]
    with ThreadPoolExecutor(max_workers=10) as ex:
        futs = {ex.submit(process, it): it for it in items}
        done = []
        for fu in as_completed(futs):
            try:
                done.append(fu.result())
            except Exception:
                done.append(futs[fu])
    print(json.dumps(done, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
