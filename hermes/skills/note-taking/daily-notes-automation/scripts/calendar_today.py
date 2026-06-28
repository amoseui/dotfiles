#!/usr/bin/env python3
"""PRIMARY 계정의 선택한 캘린더들에서 오늘(KST) 일정을 합쳐 bullet로 출력.

PRIMARY 계정 id는 config.yaml(accounts.primary)에서 읽는다.
이 계정엔 캘린더가 여러 개고 실제 일정은 보조 캘린더(약속/회사/운동/생일 등)에 있다.
google_api.py CLI는 primary만 조회하므로, 여기서는 google_api 모듈을 직접 import해
INCLUDE_CALENDARS(이름 부분매칭)에 해당하는 캘린더만 합친다.

포함 캘린더(사용자 선택): 개인(primary), 약속, 회사, 운동, 생일, 수원삼성 경기일정
제외: 대한민국의 휴일, KBO LG 트윈스 (구독성 노이즈)

출력: `* HH:MM-HH:MM 일정제목` (종일은 `* (종일) 제목`), 없으면 `* 오늘 일정 없음`.
시각순 정렬. 대괄호 [ ]는 ( )로 치환(daily note 규칙).

사용:
  calendar_today.py            # 오늘(KST)
  calendar_today.py 2026-06-28 # 특정 날짜(KST)
"""
import os, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _config

KST = timezone(timedelta(hours=9))
HOME = Path.home()
GW_SCRIPTS = HOME / ".hermes/skills/productivity/google-workspace/scripts"
# PRIMARY 계정(Gmail+Calendar). 개인 식별값은 config.yaml에만 둔다.
PRIMARY = _config.get("accounts.primary", "primary")
ACCOUNT_HOME = HOME / ".hermes/google-accounts" / PRIMARY

# 포함할 캘린더 이름(부분매칭, 대소문자 무시). primary는 항상 포함.
INCLUDE_CALENDARS = _config.get("calendars_include", [])


def hhmm(iso):
    if not iso or "T" not in iso:
        return None
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(KST).strftime("%H:%M")
    except Exception:
        return None


def clean(s):
    return (s or "").replace("[", "(").replace("]", ")").strip()


def included(cal):
    if cal.get("primary"):
        return True
    name = (cal.get("summary") or "").lower()
    return any(k.lower() in name for k in INCLUDE_CALENDARS)


def main():
    day = sys.argv[1] if len(sys.argv) > 1 else datetime.now(KST).strftime("%Y-%m-%d")
    if not (ACCOUNT_HOME / "google_token.json").exists():
        print(f"* 오늘 일정 없음 ({PRIMARY} 미인증)")
        return
    # google_api 모듈을 PRIMARY HERMES_HOME으로 로드
    os.environ["HERMES_HOME"] = str(ACCOUNT_HOME)
    sys.path.insert(0, str(GW_SCRIPTS))
    try:
        import google_api as g
        svc = g.build_service("calendar", "v3")
    except Exception as e:
        print(f"* 오늘 일정 없음 (캘린더 서비스 로드 실패: {e})")
        return

    # KST 하루를 UTC Z 범위로
    t_min = f"{day}T00:00:00+09:00"
    t_max = f"{day}T23:59:59+09:00"

    items = []
    try:
        cals = svc.calendarList().list().execute().get("items", [])
    except Exception as e:
        print(f"* 오늘 일정 없음 (캘린더 목록 조회 실패: {e})")
        return

    for cal in cals:
        if not included(cal):
            continue
        try:
            evs = svc.events().list(
                calendarId=cal["id"], timeMin=_to_utc(t_min), timeMax=_to_utc(t_max),
                singleEvents=True, orderBy="startTime",
            ).execute().get("items", [])
        except Exception:
            continue
        for ev in evs:
            start = ev.get("start", {})
            end = ev.get("end", {})
            s_iso = start.get("dateTime") or start.get("date")
            e_iso = end.get("dateTime") or end.get("date")
            summary = clean(ev.get("summary", "(제목 없음)"))
            s, e = hhmm(s_iso), hhmm(e_iso)
            # 정렬키: 시각 있으면 그 시각, 종일은 맨 앞(00:00)
            sort_key = s or "00:00"
            if s and e:
                items.append((sort_key, f"* {s}-{e} {summary}"))
            elif s:
                items.append((sort_key, f"* {s} {summary}"))
            else:
                items.append((sort_key, f"* (종일) {summary}"))

    items.sort(key=lambda x: x[0])
    print("\n".join(line for _, line in items) if items else "* 오늘 일정 없음")


def _to_utc(iso_kst):
    """'YYYY-MM-DDTHH:MM:SS+09:00' → UTC 'Z' (events.list timeMin/timeMax용)."""
    dt = datetime.fromisoformat(iso_kst).astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


if __name__ == "__main__":
    main()
