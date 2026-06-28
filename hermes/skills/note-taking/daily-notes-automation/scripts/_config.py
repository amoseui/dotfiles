#!/usr/bin/env python3
"""note-taking 스킬 공유 config 로더 (stdlib 전용, PyYAML 불필요).

개인 식별 값(계정명/경로/캘린더 등)은 모두
  ~/.hermes/skills/note-taking/hermes/config.yaml
에만 두고, 각 스크립트는 이 모듈로 읽는다. SKILL/스크립트 본문엔
개인값을 하드코딩하지 않는다 (git에 남기지 않기 위함).

지원하는 YAML 부분집합:
  - key: value            (스칼라)
  - key:                  + 들여쓴 "  child: value"  (1단계 중첩 dict)
  - key:                  + 들여쓴 "  - item"        (문자열 리스트)
인라인 주석은 값에 쓰지 않는다는 config 규약을 전제로 한다.
"""
import os
from pathlib import Path

HOME = Path.home()
# 심볼릭 링크를 따라가도 실제 경로로 해석됨.
# config.yaml(개인값, gitignore)을 우선 쓰고, 없으면 config.example.yaml로 폴백.
_CONFIG_DIR = HOME / ".hermes/skills/note-taking/hermes"
CONFIG_PATH = _CONFIG_DIR / "config.yaml"
_EXAMPLE_PATH = _CONFIG_DIR / "config.example.yaml"


def _config_file():
    if CONFIG_PATH.exists():
        return CONFIG_PATH
    return _EXAMPLE_PATH


def _strip(v):
    v = v.strip()
    if len(v) >= 2 and v[0] in "\"'" and v[-1] == v[0]:
        v = v[1:-1]
    return v


def load():
    """config.yaml(없으면 config.example.yaml)을 dict로 파싱. 둘 다 없으면 빈 dict."""
    data = {}
    cfg = _config_file()
    if not cfg.exists():
        return data
    cur_key = None        # 현재 중첩 블록의 부모 키
    cur_kind = None       # "dict" | "list"
    for raw in cfg.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        line = raw.strip()
        if indent == 0:
            # 최상위 키
            if line.endswith(":"):
                cur_key = line[:-1].strip()
                cur_kind = None  # 다음 줄 보고 dict/list 결정
                data[cur_key] = None
            elif ":" in line:
                k, _, v = line.partition(":")
                data[k.strip()] = _strip(v)
                cur_key = None
        else:
            # 중첩 항목
            if cur_key is None:
                continue
            if line.startswith("- "):
                if cur_kind != "list":
                    data[cur_key] = []
                    cur_kind = "list"
                data[cur_key].append(_strip(line[2:]))
            elif ":" in line:
                if cur_kind != "dict":
                    data[cur_key] = {}
                    cur_kind = "dict"
                k, _, v = line.partition(":")
                data[cur_key][k.strip()] = _strip(v)
    return data


def get(key, default=None):
    """점 표기 지원: get('accounts.primary'). 반환은 str|list|dict|None."""
    data = load()
    cur: object = data
    for part in key.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return default
    return cur if cur is not None else default


def as_bool(val, default=False):
    if isinstance(val, bool):
        return val
    if val is None:
        return default
    return str(val).strip().lower() in ("1", "true", "yes", "on")


if __name__ == "__main__":
    import json
    import sys as _sys
    # `_config.py --shell` → 셸에서 eval 할 수 있는 export 구문 출력.
    # 예: eval "$(python3 .../_config.py --shell)"  →  $CFG_vault_path 등 사용.
    if len(_sys.argv) > 1 and _sys.argv[1] == "--shell":
        flat = load()
        def emit(k, v):
            if isinstance(v, str):
                v = v.replace("'", "'\\''")
                print(f"CFG_{k}='{v}'")
        for k, v in flat.items():
            if isinstance(v, dict):
                for sk, sv in v.items():
                    emit(f"{k}_{sk}", sv)
            elif isinstance(v, list):
                # 리스트는 개행 구분 문자열로
                joined = "\n".join(str(x) for x in v).replace("'", "'\\''")
                print(f"CFG_{k}='{joined}'")
            else:
                emit(k, v)
    else:
        print(json.dumps(load(), ensure_ascii=False, indent=2))
