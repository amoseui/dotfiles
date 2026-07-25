#!/usr/bin/env python3
"""OPML의 RSS 피드들에서 최근 N시간 내 새 글을 수집한다.

- feeds.opml 파싱 → xmlUrl 목록
- 각 피드를 병렬로 fetch (타임아웃/에러는 조용히 skip)
- pubDate가 lookback 윈도우 내인 항목만
- rss-seen.json 에 이미 있는 링크는 제외, 새로 본 링크는 추가
- 출력: JSON 배열 [{feed_title, title, link, published, summary}]

usage: rss_new.py [lookback_hours]   (기본 26)
"""
import sys, json, pathlib, re, xml.etree.ElementTree as ET
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

PIPE = pathlib.Path.home() / ".hermes/feed-pipeline"
OPML = PIPE / "feeds.opml"
SEEN_FILE = PIPE / "rss-seen.json"
UA = "Mozilla/5.0 (feed-pipeline)"


def parse_opml():
    """OPML이 엄격한 XML이 아닐 수 있어(unescaped &) 정규식으로 추출."""
    text = OPML.read_text(encoding="utf-8", errors="replace")
    feeds = []
    for m in re.finditer(r'<outline\b[^>]*>', text):
        tag = m.group(0)
        url_m = re.search(r'xmlUrl="([^"]+)"', tag)
        if not url_m:
            continue
        url = url_m.group(1).strip()
        title_m = re.search(r'(?:title|text)="([^"]*)"', tag)
        title = (title_m.group(1).strip() if title_m else "") or url
        feeds.append((title, url))
    return feeds


def load_seen():
    if SEEN_FILE.exists():
        try:
            return set(json.loads(SEEN_FILE.read_text()).get("links", []))
        except Exception:
            return set()
    return set()


def save_seen(seen):
    # 너무 커지지 않게 최근 5000개만 유지
    SEEN_FILE.write_text(json.dumps({"links": list(seen)[-5000:]}, ensure_ascii=False))


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read()


def parse_date(s):
    if not s:
        return None
    s = s.strip()
    try:
        return parsedate_to_datetime(s)
    except Exception:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(s.replace("Z", "+0000") if fmt.endswith("%z") else s, fmt)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except Exception:
            continue
    return None


def strip_html(s):
    return re.sub(r"<[^>]+>", "", s or "").strip()[:300]


def extract_items(raw, cutoff):
    """RSS(item) + Atom(entry) 둘 다 처리. cutoff 이후 항목만."""
    out = []
    try:
        root = ET.fromstring(raw)
    except Exception:
        return out
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    # RSS
    for it in root.iter("item"):
        link = (it.findtext("link") or "").strip()
        title = (it.findtext("title") or "").strip()
        pub = parse_date(it.findtext("pubDate") or it.findtext("{http://purl.org/dc/elements/1.1/}date"))
        summ = strip_html(it.findtext("description") or "")
        if link and (pub is None or pub >= cutoff):
            out.append((title, link, pub, summ))
    # Atom
    for it in root.iter("{http://www.w3.org/2005/Atom}entry"):
        title = (it.findtext("{http://www.w3.org/2005/Atom}title") or "").strip()
        link = ""
        for l in it.findall("{http://www.w3.org/2005/Atom}link"):
            if l.get("rel") in (None, "alternate"):
                link = l.get("href", "")
                break
        pub = parse_date(it.findtext("{http://www.w3.org/2005/Atom}updated")
                         or it.findtext("{http://www.w3.org/2005/Atom}published"))
        summ = strip_html(it.findtext("{http://www.w3.org/2005/Atom}summary") or "")
        if link and (pub is None or pub >= cutoff):
            out.append((title, link, pub, summ))
    return out


def main():
    hours = int(sys.argv[1]) if len(sys.argv) > 1 else 26
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    feeds = parse_opml()
    seen = load_seen()
    results = []

    def work(ft_url):
        ftitle, url = ft_url
        try:
            raw = fetch(url)
        except Exception:
            return []
        items = extract_items(raw, cutoff)
        return [(ftitle, t, l, p, s) for (t, l, p, s) in items]

    with ThreadPoolExecutor(max_workers=20) as ex:
        futs = [ex.submit(work, f) for f in feeds]
        for fu in as_completed(futs):
            try:
                for ftitle, t, l, p, s in fu.result():
                    if l in seen:
                        continue
                    seen.add(l)
                    results.append({
                        "feed_title": ftitle, "title": t, "link": l,
                        "published": p.isoformat() if p else None, "summary": s,
                    })
            except Exception:
                continue

    results.sort(key=lambda r: r.get("published") or "", reverse=True)
    save_seen(seen)
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
