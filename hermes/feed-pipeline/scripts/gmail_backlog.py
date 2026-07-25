#!/usr/bin/env python3
"""Gmail 뉴스레터 backlog: 각 계정에서 '제일 오래된' 안 읽은 메일을 N개씩.

Gmail API를 직접 pageToken으로 끝까지 페이지네이션해서 안 읽은 메일 전체 id를
모은 뒤, internalDate(수신 시각) 오름차순 정렬 → 가장 오래된 N개의 상세를 가져온다.
(google_api.py의 gmail search는 pageToken 미지원이라 직접 호출한다.)

계정 토큰: ~/.hermes/google-accounts/<id>/google_token.json
google-workspace 스크립트의 get_credentials()를 HERMES_HOME 전환으로 재사용.

newsletter-senders.json 의 senders[] 가 있으면 그 발신자만, 없으면
category:updates/promotions/forums 후보를 대상으로 한다.

출력: JSON {account: [ {id,from,subject,date,snippet,link}, ... ]}  (오래된 것부터)
usage: gmail_backlog.py [N]   (기본 30, 계정당)
"""
import os, sys, json, pathlib, importlib, base64, re, urllib.parse, urllib.request

HOME = pathlib.Path.home()
GWS_SCRIPTS = HOME / ".hermes/skills/productivity/google-workspace/scripts"
PIPE = HOME / ".hermes/feed-pipeline"
SENDERS_FILE = PIPE / "newsletter-senders.json"
ACCOUNTS = ["amoseui", "prenine"]

sys.path.insert(0, str(GWS_SCRIPTS))


def load_senders():
    if SENDERS_FILE.exists():
        try:
            return set(s.lower() for s in json.loads(SENDERS_FILE.read_text()).get("senders", []))
        except Exception:
            return set()
    return set()


def build_gmail_for(account):
    """HERMES_HOME을 계정 폴더로 바꿔 google_api 모듈을 (재)로드 → 그 계정 토큰으로 gmail 서비스."""
    os.environ["HERMES_HOME"] = str(HOME / ".hermes/google-accounts" / account)
    # _hermes_home / google_api 모듈은 import 시점 HERMES_HOME을 캐시하므로 재로드 필요
    for m in ("google_api", "_hermes_home"):
        if m in sys.modules:
            importlib.reload(sys.modules[m])
    import _hermes_home  # noqa
    importlib.reload(_hermes_home)
    import google_api
    importlib.reload(google_api)
    return google_api.build_service("gmail", "v1")


def list_all_unread_ids(svc, query):
    ids, token = [], None
    while True:
        resp = svc.users().messages().list(
            userId="me", q=query, maxResults=500, pageToken=token
        ).execute()
        ids.extend(m["id"] for m in resp.get("messages", []))
        token = resp.get("nextPageToken")
        if not token:
            break
    return ids


SKIP_LINK = re.compile(
    r"(unsubscribe|구독취소|수신거부|mailto:|javascript:|facebook\.com|twitter\.com|x\.com/|instagram\.com|linkedin\.com/share|/share|utm_|list-manage|stibee\.com/.*?/unsubscribe)",
    re.I,
)


def _b64(data):
    if not data:
        return ""
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("utf-8", errors="replace")


def walk_parts(part):
    yield part
    for p in part.get("parts", []) or []:
        yield from walk_parts(p)


def clean_html(s):
    s = re.sub(r"<(script|style|head|svg)\b.*?</\1>", " ", s or "", flags=re.S | re.I)
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"</p>|</div>|</li>|</tr>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    repl = {"&nbsp;": " ", "&amp;": "&", "&lt;": "<", "&gt;": ">", "&#39;": "'", "&quot;": '"'}
    for k, v in repl.items():
        s = s.replace(k, v)
    s = re.sub(r"[ \t\u200b\u00ad\u034f]+", " ", s)
    s = re.sub(r"\n\s*\n+", "\n\n", s)
    return s.strip()


def resolve_url(href):
    """트래킹 링크를 따라가 최종 URL 반환. 실패하면 원본."""
    try:
        req = urllib.request.Request(href, headers={"User-Agent": "Mozilla/5.0"}, method="GET")
        with urllib.request.urlopen(req, timeout=3) as r:
            return r.geturl()
    except Exception:
        return href


def extract_links(html):
    links, seen = [], set()
    for m in re.finditer(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html or "", re.S | re.I):
        href = m.group(1).strip()
        text = clean_html(m.group(2))[:120]
        if not href or href.startswith("#") or SKIP_LINK.search(href):
            continue
        if len(text) < 3:
            continue
        if href in seen:
            continue
        seen.add(href)
        final = resolve_url(href)
        links.append({"text": text, "href": final, "tracking_href": href if final != href else None})
        if len(links) >= 5:
            break
    for href in re.findall(r"https?://[^\s<>\)\]]+", html or ""):
        href = href.rstrip('.,')
        if href not in seen and not SKIP_LINK.search(href):
            final = resolve_url(href)
            links.append({"text": final[:80], "href": final, "tracking_href": href if final != href else None})
            seen.add(href)
            if len(links) >= 5:
                break
    return links


def get_meta(svc, mid):
    msg = svc.users().messages().get(userId="me", id=mid, format="full").execute()
    hdrs = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
    htmls, plains = [], []
    for p in walk_parts(msg.get("payload", {})):
        data = p.get("body", {}).get("data")
        if not data:
            continue
        mt = p.get("mimeType", "")
        decoded = _b64(data)
        if mt == "text/html":
            htmls.append(decoded)
        elif mt == "text/plain":
            plains.append(decoded)
    html = "\n".join(htmls)
    plain = "\n".join(plains)
    body = clean_html(html) if html else clean_html(plain)
    return {
        "id": mid,
        "from": hdrs.get("From", ""),
        "subject": hdrs.get("Subject", ""),
        "date": hdrs.get("Date", ""),
        "snippet": msg.get("snippet", ""),
        "body_excerpt": body[:1500],
        "inner_links": extract_links(html or plain),
        "internalDate": int(msg.get("internalDate", "0")),
        "link": "https://mail.google.com/mail/u/0/#all/%s" % mid,
    }


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    senders = load_senders()
    result = {}
    for acct in ACCOUNTS:
        tokfile = HOME / ".hermes/google-accounts" / acct / "google_token.json"
        if not tokfile.exists():
            result[acct] = []
            continue
        try:
            svc = build_gmail_for(acct)
        except Exception as e:
            result[acct] = [{"error": "auth/build failed: %s" % e}]
            continue
        if senders:
            from_q = " OR ".join("from:%s" % s for s in sorted(senders))
            query = "is:unread (%s)" % from_q
        else:
            query = "is:unread (category:updates OR category:promotions OR category:forums)"
        ids = list_all_unread_ids(svc, query)
        # 상세는 비싸니, 일단 모든 id의 internalDate만으로 정렬하려면 각 get 필요.
        # 절충: id 전체를 받되 상세는 넉넉히(N*4)만 가져와 internalDate로 정렬 후 N개.
        # Gmail list는 최신순이므로 '오래된 것'은 리스트의 뒤쪽. 뒤에서 N*4개를 상세조회.
        tail = ids[-(n * 4):] if len(ids) > n * 4 else ids
        metas = []
        for mid in tail:
            try:
                metas.append(get_meta(svc, mid))
            except Exception:
                continue
        metas.sort(key=lambda m: m["internalDate"])  # 오래된 것 먼저
        result[acct] = [
            {k: m.get(k) for k in ("id", "from", "subject", "date", "snippet", "body_excerpt", "inner_links", "link")}
            for m in metas[:n]
        ]
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
