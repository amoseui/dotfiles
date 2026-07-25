#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
DRY_RUN=false
SKIP_BREW=false
STAMP=$(date +%Y%m%d%H%M%S)
HERMES_HOME_DIR=${HERMES_HOME:-$HOME/.hermes}
HERMES_PY="$HERMES_HOME_DIR/hermes-agent/venv/bin/python"
RESTORE_HELPER="$ROOT/scripts/hermes_restore_transaction.py"

usage() {
    echo "Usage: $0 [--dry-run] [--skip-brew]"
}

while [ $# -gt 0 ]; do
    case "$1" in
        --dry-run) DRY_RUN=true ;;
        --skip-brew) SKIP_BREW=true ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
    esac
    shift
done

run() {
    if $DRY_RUN; then
        printf '[dry-run]'
        printf ' %q' "$@"
        printf '\n'
    else
        "$@"
    fi
}

backup_file() {
    local dst=$1
    if [ -e "$dst" ] || [ -L "$dst" ]; then
        run cp -pP "$dst" "$dst.backup.$STAMP"
    fi
}

install_file() {
    local mode=$1 src=$2 dst=$3
    [ -f "$src" ] || { echo "Missing backup asset: $src" >&2; exit 1; }
    run mkdir -p "$(dirname "$dst")"
    if [ -f "$dst" ] && [ ! -L "$dst" ] && cmp -s "$src" "$dst"; then
        run chmod "$mode" "$dst"
        printf 'Unchanged: %s\n' "$dst"
        return 0
    fi
    backup_file "$dst"
    # These files are rewritten atomically by their applications. Ensure an old
    # symlink cannot survive the restore and later be replaced unexpectedly.
    if [ -L "$dst" ]; then
        run rm -f "$dst"
    fi
    run install -m "$mode" "$src" "$dst"
}

# Fail before making partial changes when destination prerequisites are absent.
if ! command -v hermes >/dev/null 2>&1; then
    echo "Hermes is not installed. Install it, then rerun:" >&2
    echo "  curl -fsSLo /tmp/hermes-install.sh https://hermes-agent.nousresearch.com/install.sh" >&2
    echo "  less /tmp/hermes-install.sh  # inspect first" >&2
    echo "  bash /tmp/hermes-install.sh" >&2
    exit 1
fi
[ -x "$HERMES_PY" ] || { echo "Hermes Python not found: $HERMES_PY" >&2; exit 1; }
if ! $DRY_RUN && [ ! -f "$HERMES_HOME_DIR/.env" ]; then
    echo "Missing $HERMES_HOME_DIR/.env" >&2
    echo "Create it from hermes/.env.example and transfer real secrets securely (never via Git)." >&2
    exit 1
fi
if ! $DRY_RUN && ! grep -q '^TODOIST_API_TOKEN=.' "$HERMES_HOME_DIR/.env"; then
    echo "TODOIST_API_TOKEN is missing from $HERMES_HOME_DIR/.env" >&2
    exit 1
fi

required_assets=(
    "$ROOT/karabiner/karabiner.json"
    "$ROOT/hermes/config.yaml"
    "$ROOT/hermes/SOUL.md"
    "$ROOT/hermes/cron/jobs.json"
    "$ROOT/hermes/scripts/chromium_docs_check.py"
    "$RESTORE_HELPER"
)
for asset in "${required_assets[@]}"; do
    [ -f "$asset" ] || { echo "Missing backup asset: $asset" >&2; exit 1; }
done

# Parse every mutable source before package installs, links, backups, gateway
# control, or destination writes.
"$HERMES_PY" - \
    "$ROOT/hermes/config.yaml" \
    "$ROOT/hermes/cron/jobs.json" \
    "$ROOT/hermes/scripts/chromium_docs_check.py" \
    "$ROOT/karabiner/karabiner.json" <<'PY'
from pathlib import Path
import json, sys, yaml

config_path, jobs_path, script_path, karabiner_path = map(Path, sys.argv[1:])
config = yaml.safe_load(config_path.read_text()) or {}
if "command_allowlist" in config:
    raise SystemExit("Refusing to restore machine-local command_allowlist")
json.loads(jobs_path.read_text())
compile(script_path.read_text(), str(script_path), "exec")
json.loads(karabiner_path.read_text())
PY

if ! $SKIP_BREW; then
    [ -f "$ROOT/Brewfile" ] || { echo "Missing backup asset: $ROOT/Brewfile" >&2; exit 1; }
    [ -x /opt/homebrew/bin/brew ] || {
        echo "Install Apple Silicon Homebrew first: https://brew.sh" >&2
        exit 1
    }
fi

if ! $SKIP_BREW; then
    run env HOMEBREW_NO_AUTO_UPDATE=1 /opt/homebrew/bin/brew bundle --file="$ROOT/Brewfile"
fi

# Stable dotfiles are symlinked by the repository's idempotent linker.
if $DRY_RUN; then
    echo "[dry-run] $ROOT/link.sh"
else
    "$ROOT/link.sh"
fi

gateway_is_running() {
    local command
    while IFS= read -r command; do
        case "$command" in
            "$HERMES_PY -m hermes_cli.main gateway run"*) return 0 ;;
        esac
    done < <(ps -axo command=)
    return 1
}

GATEWAY_WAS_RUNNING=false
GATEWAY_STOPPED=false
RESTORE_ACTIVE=false
MANIFEST=""

restore_cleanup() {
    local status=$?
    trap - EXIT
    if [ "$status" -ne 0 ]; then
        if $RESTORE_ACTIVE && [ -n "$MANIFEST" ] && [ -f "$MANIFEST" ]; then
            "$HERMES_PY" "$RESTORE_HELPER" rollback "$MANIFEST" || {
                echo "Automatic Hermes rollback failed; inspect: $MANIFEST" >&2
                status=1
            }
            RESTORE_ACTIVE=false
        fi
        if $GATEWAY_WAS_RUNNING && $GATEWAY_STOPPED; then
            hermes gateway start >/dev/null || {
                echo "The previously running Hermes gateway could not be restarted." >&2
                status=1
            }
            GATEWAY_STOPPED=false
        fi
    fi
    exit "$status"
}
trap restore_cleanup EXIT

if $DRY_RUN; then
    echo "[dry-run] stop and verify Hermes gateway if running"
    echo "[dry-run] transactional Hermes restore with rollback on failed validation"
else
    if gateway_is_running; then
        GATEWAY_WAS_RUNNING=true
        hermes gateway stop >/dev/null
        for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
            gateway_is_running || break
            sleep 0.25
        done
        gateway_is_running && {
            echo "Hermes gateway is still running; refusing mutable-file restore." >&2
            exit 1
        }
        GATEWAY_STOPPED=true
    fi

    MANIFEST=$("$HERMES_PY" "$RESTORE_HELPER" apply \
        --root "$ROOT" --hermes-home "$HERMES_HOME_DIR" --stamp "$STAMP")
    RESTORE_ACTIVE=true
    if ! hermes config check || ! hermes cron list; then
        echo "Hermes validation failed; rolling back the pre-migration files." >&2
        exit 1
    fi
    "$HERMES_PY" "$RESTORE_HELPER" commit "$MANIFEST"
    RESTORE_ACTIVE=false
    if $GATEWAY_WAS_RUNNING; then
        hermes gateway start >/dev/null || {
            echo "Restore succeeded, but the previously running Hermes gateway could not be restarted." >&2
            exit 1
        }
        GATEWAY_STOPPED=false
    fi
fi

# Karabiner also rewrites this file, but it is independent of the Hermes group.
install_file 644 "$ROOT/karabiner/karabiner.json" "$HOME/.config/karabiner/karabiner.json"

if $DRY_RUN; then
    echo "Dry run complete; no changes made."
else
    cat <<'EOF'
Restore complete. Before starting the gateway:
  1. Finish ~/.hermes/.env and OAuth/service logins.
  2. Securely transfer Google account token directories if needed.
  3. Run: hermes doctor
  4. Run: hermes gateway start
EOF
fi
