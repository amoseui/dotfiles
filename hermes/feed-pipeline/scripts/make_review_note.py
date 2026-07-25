#!/usr/bin/env python3
"""Feed/Gmail/Readwise JSON을 Obsidian 체크박스 리뷰 큐 노트로 만든다.

입력 파일:
  --gmail /tmp/fp_gmail.json        gmail_backlog.py 출력
  --reader /tmp/fp_reader_full.json reader_backlog.py | fetch_content.py 출력
  --rss /tmp/fp_rss_full.json       rss_new.py | fetch_content.py 출력

출력:
  /Users/amoseui/Obsidian/amoseui/amoseui/hermes/review/YYYY-MM-DD-feed-review.md

체크박스 프로토콜:
  APPLY 전에는 아무것도 처리하지 않음.
  각 항목: NL+/NL-/KEEP/MERGE/SKIP/READ 체크박스.
"""
import argparse, json, pathlib, re
from datetime import datetime

VAULT = pathlib.Path("/Users/amoseui/Obsidian/amoseui/amoseui")
OUT_DIR = VAULT / "hermes/review"

def load(path):
    if not path:
        return None
    p = pathlib.Path(path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None

def clean(s, n=500):
    s = re.sub(r"\s+", " ", s or "").strip()
    return s[:n]

def short_date(s):
    s = s or ""
    m = re.search(r"\d{4}-\d{2}-\d{2}", s)
    if m:
        return m.group(0)
    # Gmail RFC date: Wed, 15 May 2024 ... -> 2024-05-15 근사
    m = re.search(r"(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})", s)
    if m:
        mon = {'Jan':'01','Feb':'02','Mar':'03','Apr':'04','May':'05','Jun':'06','Jul':'07','Aug':'08','Sep':'09','Oct':'10','Nov':'11','Dec':'12'}.get(m.group(2),'??')
        return f"{m.group(3)}-{mon}-{int(m.group(1)):02d}"
    return s[:10]

def links_md(links, prefix, parent_date=""):
    out=[]
    for i,l in enumerate((links or [])[:3],1):
        lid=f"{prefix}:L{i}"
        text=clean(l.get('text'),80) or f"link {i}"
        href=l.get('href') or ''
        date_note = f" — 날짜: {parent_date}" if parent_date else ""
        # 세부 링크 자체 발행일을 모르면 부모 항목 날짜를 붙인다.
        out.append(f"  - {lid} [{text}]({href}){date_note}")
        out.append(f"    - [ ] {lid} KEEP — 이 세부 링크를 위키에 저장 후보")
        out.append(f"    - [ ] {lid} SKIP — 이 세부 링크 버림")
    return "\n".join(out)

def newsletter_pred(m):
    txt=(m.get('subject','')+' '+m.get('from','')+' '+(m.get('body_excerpt') or m.get('snippet') or '')).lower()
    y=any(x in txt for x in ['뉴스레터','레터','issue','vol.','구독','지난호','weekly','digest','소식','큐레이션','웹에서 보기'])
    return 'Y' if y else '?'

def item_block(id_, title, source, link, summary, inner_links, kind, pred='', date_label=''):
    lines=[f"### {id_}. {title}", ""]
    if pred:
        lines.append(f"- 예측: {pred}")
    if date_label:
        lines.append(f"- 날짜: {date_label}")
    lines.append(f"- 출처: {source}")
    if link:
        lines.append(f"- 링크: {link}")
    if summary:
        lines.append(f"- 요약: {summary}")
    if inner_links:
        lines.append("- 세부링크:")
        lm=links_md(inner_links, id_, date_label)
        if lm: lines.append(lm)
    lines += [
        "",
        f"- [ ] {id_} NL+ — 뉴스레터 발신자 저장" if kind=='email' else f"- [ ] {id_} MERGE — 기존 위키 페이지 병합 후보",
        f"- [ ] {id_} NL- — 뉴스레터 아님/제외" if kind=='email' else f"- [ ] {id_} KEEP — 위키에 저장 후보",
    ]
    if kind == 'email':
        lines.append(f"- [ ] {id_} KEEP — 위키에 저장 후보")
    lines += [
        f"- [ ] {id_} SKIP — 버림",
        f"- [ ] {id_} READ — 읽음 처리/소진",
        "",
    ]
    return "\n".join(lines)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--gmail')
    ap.add_argument('--reader')
    ap.add_argument('--rss')
    ap.add_argument('--date', default=datetime.now().strftime('%Y-%m-%d'))
    args=ap.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out=OUT_DIR / f"{args.date}-feed-review.md"

    parts=["---", f"title: Feed Review {args.date}", f"created: {datetime.now().isoformat(timespec='seconds')}", "type: review", "tags: [feed-review, hermes]", "---", "", f"# Feed Review {args.date}", "", "- [ ] APPLY — 체크하면 Hermes가 선택사항을 실행", "", "> APPLY 전에는 아무것도 변경되지 않음. 체크만 해두고 나중에 Hermes가 처리.", ""]

    gmail=load(args.gmail)
    if isinstance(gmail, dict):
        for acct,prefix in [('amoseui','A'),('prenine','P')]:
            items=gmail.get(acct) or []
            if items:
                parts += [f"## Email — {acct}", ""]
                for i,m in enumerate(items,1):
                    id_=f"{prefix}{i}"
                    pred=f"뉴스레터 {newsletter_pred(m)}"
                    date_label=f"이메일 송신: {short_date(m.get('date'))}"
                    parts.append(item_block(id_, m.get('subject','(no subject)'), m.get('from',''), m.get('link',''), clean(m.get('body_excerpt') or m.get('snippet'), 350), m.get('inner_links') or [], 'email', pred, date_label))

    for label,path,prefix in [('Readwise', args.reader, 'R'), ('RSS 신규', args.rss, 'F')]:
        items=load(path)
        if isinstance(items, list) and items:
            parts += [f"## {label}", ""]
            for i,it in enumerate(items,1):
                id_=f"{prefix}{i}"
                title=it.get('title') or '(no title)'
                source=it.get('site_name') or it.get('feed_title') or it.get('author') or ''
                link=it.get('source_url') or it.get('link') or it.get('url') or ''
                summary=clean(it.get('body_excerpt') or it.get('summary') or '', 350)
                if prefix == 'R':
                    date_bits=[]
                    if it.get('created_at'):
                        date_bits.append(f"Readwise 추가: {short_date(it.get('created_at'))}")
                    if it.get('published_date'):
                        date_bits.append(f"원문 발행: {short_date(it.get('published_date'))}")
                    date_label=" / ".join(date_bits)
                else:
                    date_label=f"RSS 발행: {short_date(it.get('published'))}" if it.get('published') else ""
                parts.append(item_block(id_, title, source, link, summary, it.get('inner_links') or [], 'reader', '위키 판단 필요', date_label))

    out.write_text("\n".join(parts))
    print(str(out))

if __name__ == '__main__':
    main()
