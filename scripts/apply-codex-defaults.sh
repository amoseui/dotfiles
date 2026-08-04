#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
CODEX_HOME_DIR=${CODEX_HOME:-$HOME/.codex}
CONFIG="$CODEX_HOME_DIR/config.toml"
DEFAULTS="$ROOT/codex/defaults.toml"

mkdir -p "$CODEX_HOME_DIR"

python3 - "$CONFIG" "$DEFAULTS" <<'PY'
from pathlib import Path
import os, re, sys, tempfile

config_path, defaults_path = map(Path, sys.argv[1:])
config = config_path.read_text() if config_path.exists() else ""
defaults = {}
for line in defaults_path.read_text().splitlines():
    line = line.strip()
    if not line or line.startswith("#"):
        continue
    key, value = line.split("=", 1)
    defaults[key.strip()] = value.strip()

for key, value in defaults.items():
    pattern = re.compile(rf"(?m)^{re.escape(key)}\s*=.*$")
    replacement = f"{key} = {value}"
    if pattern.search(config):
        config = pattern.sub(replacement, config, count=1)
    else:
        config = replacement + "\n" + config

if config and not config.endswith("\n"):
    config += "\n"
config_path.parent.mkdir(parents=True, exist_ok=True)
fd, tmp_name = tempfile.mkstemp(prefix=".config.toml.", dir=config_path.parent)
os.close(fd)
try:
    tmp = Path(tmp_name)
    tmp.write_text(config)
    os.chmod(tmp, 0o600)
    os.replace(tmp, config_path)
finally:
    Path(tmp_name).unlink(missing_ok=True)
PY

python3 - "$CONFIG" <<'PY'
from pathlib import Path
import re, sys
path = Path(sys.argv[1])
text = path.read_text()
required = {
    "model": '"gpt-5.6-luna"',
    "model_reasoning_effort": '"max"',
    "service_tier": '"priority"',
}
for key, value in required.items():
    if not re.search(rf"(?m)^{re.escape(key)}\s*=\s*{re.escape(value)}\s*$", text):
        raise SystemExit(f"Codex default verification failed for {key}")
print(f"Codex defaults applied: {path}")
PY
