#!/usr/bin/env bash
set -euo pipefail

SERVICES_ENV=${DOTFILES_SERVICES_ENV:-$HOME/.config/dotfiles/services.env}
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
# shellcheck source=load-services-env.sh
. "$SCRIPT_DIR/load-services-env.sh"
load_services_env "$SERVICES_ENV"

REPO=${PERSONAL_OBSERVATORY_REPO:-$HOME/Workspace/personal-observatory}
HOST=${PERSONAL_OBSERVATORY_HOST:-}
PORT=${PERSONAL_OBSERVATORY_PORT:-8788}
[[ "$PORT" =~ ^[0-9]+$ ]] || { echo "Invalid Personal Observatory port: $PORT" >&2; exit 1; }
PORT_NUMBER=$((10#$PORT))
(( PORT_NUMBER >= 1 && PORT_NUMBER <= 65535 )) || { echo "Invalid Personal Observatory port: $PORT" >&2; exit 1; }
PORT=$PORT_NUMBER
UVICORN=$REPO/.venv/bin/uvicorn

[ -f "$REPO/pyproject.toml" ] || { echo "Personal Observatory repo missing: $REPO" >&2; exit 1; }
[ -x "$UVICORN" ] || { echo "Personal Observatory venv missing: $UVICORN" >&2; exit 1; }

HOST=${HOST:-127.0.0.1}
case "$HOST" in
    127.0.0.1|localhost|::1) ;;
    *) echo "Refusing non-loopback Personal Observatory; use Tailscale Serve" >&2; exit 1 ;;
esac

cd "$REPO"
exec "$UVICORN" personal_observatory.app:app --host "$HOST" --port "$PORT"
