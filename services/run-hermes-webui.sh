#!/usr/bin/env bash
set -euo pipefail

SERVICES_ENV=${DOTFILES_SERVICES_ENV:-$HOME/.config/dotfiles/services.env}
REPO_DEFAULT=$HOME/Workspace/github/hermes-webui
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
# shellcheck source=load-services-env.sh
. "$SCRIPT_DIR/load-services-env.sh"

load_services_env "$SERVICES_ENV"

REPO=${HERMES_WEBUI_REPO:-$REPO_DEFAULT}
HOST=${HERMES_WEBUI_HOST:-}
PORT=${HERMES_WEBUI_PORT:-8787}

[[ "$PORT" =~ ^[0-9]+$ ]] || { echo "Invalid Hermes WebUI port: $PORT" >&2; exit 1; }
PORT_NUMBER=$((10#$PORT))
(( PORT_NUMBER >= 1 && PORT_NUMBER <= 65535 )) || { echo "Invalid Hermes WebUI port: $PORT" >&2; exit 1; }
PORT=$PORT_NUMBER

[ -f "$REPO/bootstrap.py" ] || { echo "Hermes WebUI repo missing: $REPO" >&2; exit 1; }
PYTHON=${HERMES_WEBUI_PYTHON:-$HOME/.hermes/hermes-agent/venv/bin/python}
[ -x "$PYTHON" ] || { echo "Hermes WebUI Python missing: $PYTHON" >&2; exit 1; }

HOST=${HOST:-127.0.0.1}
case "$HOST" in
    127.0.0.1|localhost|::1) ;;
    *) echo "Refusing non-loopback Hermes WebUI; use Tailscale Serve" >&2; exit 1 ;;
esac
# Direct TLS and application password auth are deliberately disabled. Keep
# empty values exported so bootstrap.py's repo-local .env cannot restore old
# direct-TLS/password paths. Access is bounded by loopback + Tailscale Serve.
export HERMES_WEBUI_TLS_CERT= HERMES_WEBUI_TLS_KEY=
export HERMES_WEBUI_PASSWORD=
export HERMES_WEBUI_HOST=$HOST HERMES_WEBUI_PORT=$PORT
# bootstrap.py parses the repo-local .env without executing it. Preserve the
# launcher values above, including the intentional empty password value.
export HERMES_WEBUI_PRESERVE_ENV=1
cd "$REPO"
exec "$PYTHON" bootstrap.py --no-browser --foreground --skip-agent-install \
    "$PORT" --host "$HOST"
