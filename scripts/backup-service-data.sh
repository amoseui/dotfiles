#!/usr/bin/env bash
set -euo pipefail

[ $# -eq 1 ] || { echo "Usage: $0 /path/to/encrypted-or-external-backup" >&2; exit 2; }
ROOT=$(cd "$(dirname "$0")/.." && pwd)
# shellcheck source=../services/load-services-env.sh
. "$ROOT/services/load-services-env.sh"
load_services_env "${DOTFILES_SERVICES_ENV:-$HOME/.config/dotfiles/services.env}"
DEST_ROOT=$1
STAMP=$(date +%Y%m%d%H%M%S)-$$
DEST=$DEST_ROOT/service-data-$STAMP
OBS_REPO=${PERSONAL_OBSERVATORY_REPO:-$HOME/Workspace/github/personal-observatory}
[ ! -e "$DEST" ] || { echo "Backup destination already exists: $DEST" >&2; exit 1; }
HERMES_PY=${HERMES_HOME:-$HOME/.hermes}/hermes-agent/venv/bin/python
[ -x "$HERMES_PY" ] || { echo "Hermes Python missing: $HERMES_PY" >&2; exit 1; }

mkdir -p "$DEST_ROOT"
STAGING=$(mktemp -d "$DEST_ROOT/.service-data-$STAMP.XXXXXX")
cleanup() {
    [ -n "${STAGING:-}" ] && [ -d "$STAGING" ] || return 0
    rm -f "$STAGING/personal-observatory/data/feed_state.json" \
        "$STAGING/personal-observatory/data/feed_items.json" \
        "$STAGING/MANIFEST.txt" "$STAGING/SHA256SUMS"
    rmdir "$STAGING/personal-observatory/data" "$STAGING/personal-observatory" \
        "$STAGING" 2>/dev/null || true
}
trap cleanup EXIT
chmod 700 "$STAGING"
mkdir -p "$STAGING/personal-observatory"
chmod 700 "$STAGING/personal-observatory"

"$HERMES_PY" - "$OBS_REPO" "$STAGING" <<'PY'
from pathlib import Path
import hashlib, json, sys, time, yaml

repo, dest = map(Path, sys.argv[1:])
config_path = repo / "config.local.yaml"
config = yaml.safe_load(config_path.read_text()) if config_path.is_file() else {}
feeds = (config or {}).get("feeds") or {}
specs = (
    ("feed_state.json", feeds.get("state_path"), repo / "data/feed_state.json"),
    ("feed_items.json", feeds.get("items_path"), repo / "data/feed_items.json"),
)
sources = []
for archive_name, configured, default in specs:
    candidate = Path(str(configured)).expanduser() if configured else default
    if not candidate.is_absolute():
        candidate = repo / candidate
    if not candidate.exists():
        continue
    if candidate.is_symlink() or not candidate.is_file():
        raise SystemExit(f"Refusing non-regular feed data source: {candidate}")
    source = candidate.resolve()
    sources.append((archive_name, source))
if not sources:
    raise SystemExit(f"No Personal Observatory feed data found from {config_path}")

# Read the complete set twice. Publish only when every source is byte-identical
# across the observation window, so a writer cannot produce a mixed snapshot.
snapshot = None
for attempt in range(3):
    first = {source: source.read_bytes() for _, source in sources}
    second = {source: source.read_bytes() for _, source in sources}
    if first == second:
        snapshot = first
        break
    time.sleep(0.05 * (attempt + 1))
if snapshot is None:
    raise SystemExit("Feed data changed during backup; retry when refresh/triage is idle")

copied = []
for archive_name, source in sources:
    try:
        json.loads(snapshot[source])
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Refusing invalid JSON feed data: {source}") from exc
    target = dest / "personal-observatory/data" / archive_name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.parent.chmod(0o700)
    target.write_bytes(snapshot[source])
    target.chmod(0o600)
    copied.append((target.relative_to(dest), source))
with (dest / "SHA256SUMS").open("w") as sums:
    for relative, source in copied:
        digest = hashlib.sha256((dest / relative).read_bytes()).hexdigest()
        sums.write(f"{digest}  {relative}\n")
        print(f"Copied: {source}")
PY

cat > "$STAGING/MANIFEST.txt" <<EOF
Created: $STAMP
Source: $OBS_REPO
Contains Personal Observatory local feed personalization/cache only.
Portable config is restored from the dotfiles repository, not this data archive.
Does not contain Hermes .env, auth.json, OAuth tokens, TLS private keys,
WebUI signing/auth state, logs, or Hermes session/state databases.
EOF
chmod 600 "$STAGING/MANIFEST.txt"
chmod 600 "$STAGING/SHA256SUMS"
mv "$STAGING" "$DEST"
STAGING=""
printf 'Service data backup: %s\n' "$DEST"
printf 'Transfer this directory only through an encrypted disk or secure channel.\n'
