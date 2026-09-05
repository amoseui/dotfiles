#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
CODEX_HOME_DIR=${CODEX_HOME:-$HOME/.codex}
CONFIG="$CODEX_HOME_DIR/config.toml"
DEFAULTS="$ROOT/codex/defaults.toml"

mkdir -p "$CODEX_HOME_DIR"

python3 - "$CONFIG" "$DEFAULTS" <<'PY'
from pathlib import Path
import datetime, json, os, re, sys, tempfile, tomllib

config_path, defaults_path = map(Path, sys.argv[1:])
config = config_path.read_text() if config_path.exists() else ""
original = tomllib.loads(config)
defaults = tomllib.loads(defaults_path.read_text())
allowed = {"model", "model_reasoning_effort", "service_tier", "project_doc_fallback_filenames"}
if not defaults or defaults.keys() - allowed:
    raise SystemExit("Unsupported portable default; keep machine-local tables out of defaults.toml")

# Restrict edits to the root preamble. Validate the entire resulting document
# semantically before writing, including unusual TOML such as multiline strings.
table = re.search(r"(?m)^\s*\[", config)
offset = table.start() if table else len(config)
preamble, tables = config[:offset], config[offset:]

for key, value in defaults.items():
    pattern = re.compile(rf'''(?m)^[ \t]*(?:{re.escape(key)}|"{re.escape(key)}"|'{re.escape(key)}')[ \t]*=.*$''')
    replacement = f"{key} = {json.dumps(value)}"
    match = pattern.search(preamble)
    if match:
        end = match.end()
        while True:
            try:
                parsed = tomllib.loads(preamble[match.start():end])
                if parsed != {key: original[key]}:
                    raise SystemExit(f"Cannot safely locate root value: {key}")
                break
            except tomllib.TOMLDecodeError:
                if end == len(preamble):
                    raise SystemExit(f"Cannot safely locate root value: {key}")
                newline = preamble.find("\n", end + 1)
                end = len(preamble) if newline < 0 else newline
        preamble = preamble[:match.start()] + replacement + preamble[end:]
    else:
        preamble = replacement + "\n" + preamble

config = preamble + tables
if config and not config.endswith("\n"):
    config += "\n"
expected = {**original, **defaults}
if tomllib.loads(config) != expected:
    raise SystemExit("Refusing config update: unrelated settings would change")
if config_path.exists() and config == config_path.read_text():
    print(f"Codex defaults already applied: {config_path}")
    raise SystemExit(0)
config_path.parent.mkdir(parents=True, exist_ok=True)
if config_path.exists():
    stamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
    backup = config_path.with_name(f"config.toml.old.{stamp}")
    with open(backup, "x", opener=lambda path, flags: os.open(path, flags, 0o600)) as stream:
        stream.write(config_path.read_text())
fd, tmp_name = tempfile.mkstemp(prefix=".config.toml.", dir=config_path.parent)
os.close(fd)
try:
    tmp = Path(tmp_name)
    tmp.write_text(config)
    os.chmod(tmp, 0o600)
    os.replace(tmp, config_path)
finally:
    Path(tmp_name).unlink(missing_ok=True)
if tomllib.loads(config_path.read_text()) != expected:
    raise SystemExit("Codex config verification failed")
print(f"Codex defaults applied: {config_path}")
PY
