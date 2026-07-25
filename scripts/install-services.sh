#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
# shellcheck source=../services/load-services-env.sh
. "$ROOT/services/load-services-env.sh"
DRY_RUN=false
START=false
STAMP=$(date +%Y%m%d%H%M%S)-$$
TMP_FILES=()
TRANSACTION_ACTIVE=false
TRANSACTION_MANIFEST=""
PRIOR_LOADED=()
labels=(local.hermes.webui local.personal.observatory)

usage() { echo "Usage: $0 [--dry-run] [--start]"; }
while [ $# -gt 0 ]; do
    case "$1" in
        --dry-run) DRY_RUN=true ;;
        --start) START=true ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
    esac
    shift
done

cleanup() {
    local status=$? label path
    if $TRANSACTION_ACTIVE; then
        if $START; then
            for label in "${labels[@]}"; do
                launchctl bootout "gui/$(id -u)/$label" >/dev/null 2>&1 || true
            done
        fi
        python3 "$ROOT/scripts/file_install_transaction.py" rollback "$TRANSACTION_MANIFEST" || {
            echo "Service install rollback failed; inspect: $TRANSACTION_MANIFEST" >&2
            status=1
        }
        if $START; then
            for label in "${PRIOR_LOADED[@]}"; do
                launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/$label.plist" >/dev/null 2>&1 || true
                launchctl kickstart -k "gui/$(id -u)/$label" >/dev/null 2>&1 || true
            done
        fi
    fi
    for path in "${TMP_FILES[@]}"; do [ -f "$path" ] && rm -f "$path"; done
    exit "$status"
}
trap cleanup EXIT

required=(
    "$ROOT/services/services.env.example"
    "$ROOT/services/load-services-env.sh"
    "$ROOT/services/run-hermes-webui.sh"
    "$ROOT/services/run-personal-observatory.sh"
    "$ROOT/services/personal-observatory/config.local.yaml"
    "$ROOT/launchd/local.hermes.webui.plist.template"
    "$ROOT/launchd/local.personal.observatory.plist.template"
    "$ROOT/scripts/file_install_transaction.py"
)
for path in "${required[@]}"; do [ -f "$path" ] || { echo "Missing service asset: $path" >&2; exit 1; }; done

SERVICES_ENV=$HOME/.config/dotfiles/services.env
if [ -e "$SERVICES_ENV" ]; then
    ENV_SOURCE=$SERVICES_ENV
    echo "Keeping existing: $SERVICES_ENV"
else
    ENV_SOURCE=$ROOT/services/services.env.example
fi
load_services_env "$ENV_SOURCE"

OBS_REPO=${PERSONAL_OBSERVATORY_REPO:-$HOME/Workspace/personal-observatory}
SPEC=$(mktemp)
TMP_FILES+=("$SPEC")
spec_args=()
if [ ! -e "$SERVICES_ENV" ]; then
    spec_args+=(600 "$ROOT/services/services.env.example" "$SERVICES_ENV")
fi
if [ -d "$OBS_REPO" ]; then
    spec_args+=(600 "$ROOT/services/personal-observatory/config.local.yaml" "$OBS_REPO/config.local.yaml")
else
    echo "Personal Observatory repo not cloned yet: $OBS_REPO" >&2
fi

for label in "${labels[@]}"; do
    template=$ROOT/launchd/$label.plist.template
    tmp=$(mktemp)
    TMP_FILES+=("$tmp")
    python3 - "$template" "$tmp" "$HOME" "$ROOT" <<'PY'
from pathlib import Path
import sys
src, dst = map(Path, sys.argv[1:3])
home, root = sys.argv[3:5]
dst.write_text(src.read_text().replace("__HOME__", home).replace("__DOTFILES_ROOT__", root))
PY
    plutil -lint "$tmp" >/dev/null
    spec_args+=(644 "$tmp" "$HOME/Library/LaunchAgents/$label.plist")
done

python3 - "$SPEC" "${spec_args[@]}" <<'PY'
from pathlib import Path
import json, sys
output = Path(sys.argv[1])
values = sys.argv[2:]
if len(values) % 3:
    raise SystemExit("Invalid service install spec arguments")
specs = [
    {"mode": int(values[index], 8), "source": values[index + 1], "destination": values[index + 2]}
    for index in range(0, len(values), 3)
]
output.write_text(json.dumps(specs, indent=2) + "\n")
PY

if $DRY_RUN; then
    python3 - "$SPEC" <<'PY'
import json, sys
for item in json.load(open(sys.argv[1])):
    print(f"[dry-run] install -m {item['mode']:o} {item['source']} {item['destination']}")
PY
    $START && echo "[dry-run] transactionally restart dashboard services"
    echo "Dry run complete; no service definitions installed."
    exit 0
fi

TRANSACTION_MANIFEST=$(mktemp)
rm -f "$TRANSACTION_MANIFEST"
TMP_FILES+=("$TRANSACTION_MANIFEST")
python3 "$ROOT/scripts/file_install_transaction.py" apply \
    --spec "$SPEC" --manifest "$TRANSACTION_MANIFEST" --stamp "$STAMP"
TRANSACTION_ACTIVE=true

if $START; then
    for label in "${labels[@]}"; do
        if launchctl print "gui/$(id -u)/$label" >/dev/null 2>&1; then
            PRIOR_LOADED+=("$label")
        fi
    done
    for label in "${labels[@]}"; do
        launchctl bootout "gui/$(id -u)/$label" >/dev/null 2>&1 || true
        launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/$label.plist"
        launchctl kickstart -k "gui/$(id -u)/$label"
    done
fi

python3 "$ROOT/scripts/file_install_transaction.py" commit "$TRANSACTION_MANIFEST"
TRANSACTION_ACTIVE=false

cat <<EOF
Service definitions installed.
Edit: $SERVICES_ENV
Then run: $0 --start
Hermes gateway is managed separately with: hermes gateway start
EOF