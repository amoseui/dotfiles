#!/usr/bin/env bash
set -euo pipefail

[ $# -eq 1 ] || { echo "Usage: $0 /path/to/service-data-YYYYMMDDHHMMSS-PID" >&2; exit 2; }
ROOT=$(cd "$(dirname "$0")/.." && pwd)
# shellcheck source=../services/load-services-env.sh
. "$ROOT/services/load-services-env.sh"
load_services_env "${DOTFILES_SERVICES_ENV:-$HOME/.config/dotfiles/services.env}"
SRC=$1/personal-observatory
OBS_REPO=${PERSONAL_OBSERVATORY_REPO:-$HOME/Workspace/github/personal-observatory}
STAMP=$(date +%Y%m%d%H%M%S)
HERMES_PY=${HERMES_HOME:-$HOME/.hermes}/hermes-agent/venv/bin/python

[ -d "$SRC" ] || { echo "Missing backup directory: $SRC" >&2; exit 1; }
[ -d "$OBS_REPO" ] || { echo "Personal Observatory repo not cloned: $OBS_REPO" >&2; exit 1; }
[ -s "$1/SHA256SUMS" ] || { echo "Missing or empty SHA256SUMS: $1/SHA256SUMS" >&2; exit 1; }
[ -x "$HERMES_PY" ] || { echo "Hermes Python missing: $HERMES_PY" >&2; exit 1; }

"$HERMES_PY" - "$1" "$SRC" <<'PY'
from pathlib import Path, PurePosixPath
import hashlib, json, re, sys

archive, source_root = map(Path, sys.argv[1:])
manifest_path = archive / "SHA256SUMS"
entries = {}
for line_number, line in enumerate(manifest_path.read_text().splitlines(), 1):
    match = re.fullmatch(r"([0-9a-fA-F]{64})  (.+)", line)
    if not match:
        raise SystemExit(f"Malformed SHA256SUMS line {line_number}")
    digest, raw_name = match.groups()
    relative = PurePosixPath(raw_name)
    if relative.is_absolute() or ".." in relative.parts or str(relative) != raw_name:
        raise SystemExit(f"Unsafe SHA256SUMS path: {raw_name}")
    if raw_name in entries:
        raise SystemExit(f"Duplicate SHA256SUMS path: {raw_name}")
    entries[raw_name] = digest.lower()

recognized = {
    f"personal-observatory/data/{name}"
    for name in ("feed_state.json", "feed_items.json")
    if (source_root / "data" / name).exists()
}
if not recognized:
    raise SystemExit(f"No recognized service data in {source_root}")
if set(entries) != recognized:
    missing = sorted(recognized - set(entries))
    unexpected = sorted(set(entries) - recognized)
    raise SystemExit(f"SHA256SUMS coverage mismatch; missing={missing} unexpected={unexpected}")

for raw_name, expected in entries.items():
    path = archive.joinpath(*PurePosixPath(raw_name).parts)
    if not path.is_file() or path.is_symlink():
        raise SystemExit(f"Refusing non-regular archive file: {raw_name}")
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != expected:
        raise SystemExit(f"SHA-256 mismatch: {raw_name}")
    try:
        parsed = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Invalid JSON archive file: {raw_name}") from exc
    if not isinstance(parsed, dict):
        raise SystemExit(f"Expected JSON object in archive file: {raw_name}")
print("SHA256SUMS and JSON preflight passed")
PY

"$HERMES_PY" - "$SRC" "$OBS_REPO" "$STAMP-$$" <<'PY'
from pathlib import Path
import json, os, shutil, sys, tempfile, yaml

source_root, repo = map(Path, sys.argv[1:3])
stamp = sys.argv[3]
config_path = repo / "config.local.yaml"
config = yaml.safe_load(config_path.read_text()) if config_path.is_file() else {}
feeds = (config or {}).get("feeds") or {}
specs = (
    ("feed_state.json", feeds.get("state_path"), repo / "data/feed_state.json"),
    ("feed_items.json", feeds.get("items_path"), repo / "data/feed_items.json"),
)
prepared = []
changed = []
try:
    for archive_name, configured, default in specs:
        source = source_root / "data" / archive_name
        if not source.is_file():
            continue
        target = Path(str(configured)).expanduser() if configured else default
        if not target.is_absolute():
            target = repo / target
        target = target.resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        backup = None
        if target.exists():
            if not target.is_file() or target.is_symlink():
                raise RuntimeError(f"Refusing non-regular restore target: {target}")
            backup = Path(f"{target}.backup.{stamp}")
            if backup.exists() or backup.is_symlink():
                raise RuntimeError(f"Restore backup already exists: {backup}")
            shutil.copy2(target, backup)
        fd, temp_name = tempfile.mkstemp(prefix=f".{target.name}.restore-", dir=target.parent)
        os.close(fd)
        temp = Path(temp_name)
        shutil.copyfile(source, temp)
        with temp.open("rb") as handle:
            parsed = json.load(handle)
        if not isinstance(parsed, dict):
            raise RuntimeError(f"Expected JSON object in {source}")
        temp.chmod(0o600)
        prepared.append((target, temp, backup))
    if not prepared:
        raise RuntimeError(f"No recognized service data in {source_root}")
    for target, temp, backup in prepared:
        os.replace(temp, target)
        changed.append((target, backup))
        print(f"Restored: {target}")
except Exception:
    for target, backup in reversed(changed):
        if backup and backup.is_file():
            fd, temp_name = tempfile.mkstemp(prefix=f".{target.name}.rollback-", dir=target.parent)
            os.close(fd)
            temp = Path(temp_name)
            shutil.copy2(backup, temp)
            os.replace(temp, target)
        else:
            target.unlink(missing_ok=True)
    raise
finally:
    for _, temp, _ in prepared:
        temp.unlink(missing_ok=True)
PY