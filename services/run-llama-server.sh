#!/usr/bin/env bash
set -euo pipefail

SERVICES_ENV=${DOTFILES_SERVICES_ENV:-$HOME/.config/dotfiles/services.env}
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
# shellcheck source=load-services-env.sh
. "$SCRIPT_DIR/load-services-env.sh"
load_services_env "$SERVICES_ENV"

SERVER=${LLAMA_SERVER_BIN:-/opt/homebrew/bin/llama-server}
MODEL=${LLAMA_MODEL:-$HOME/.local/share/llama.cpp/models/Qwen3.6-27B-Q6_K.gguf}
HOST=${LLAMA_HOST:-127.0.0.1}
PORT=${LLAMA_PORT:-8080}
CONTEXT=${LLAMA_CONTEXT:-65536}

[ -x "$SERVER" ] || { echo "llama-server missing: $SERVER" >&2; exit 1; }
[ -f "$MODEL" ] || { echo "GGUF model missing: $MODEL" >&2; exit 1; }
case "$HOST" in
    127.0.0.1|localhost|::1) ;;
    *) echo "Refusing non-loopback llama-server host: $HOST" >&2; exit 1 ;;
esac
for value in "$PORT" "$CONTEXT"; do
    [[ "$value" =~ ^[0-9]+$ ]] || { echo "Invalid numeric llama-server setting: $value" >&2; exit 1; }
done
PORT=$((10#$PORT))
CONTEXT=$((10#$CONTEXT))
(( PORT >= 1 && PORT <= 65535 )) || { echo "Invalid llama-server port: $PORT" >&2; exit 1; }
(( CONTEXT >= 4096 )) || { echo "llama-server context must be at least 4096: $CONTEXT" >&2; exit 1; }

exec "$SERVER" \
    --model "$MODEL" \
    --alias qwen3.6-27b \
    --host "$HOST" \
    --port "$PORT" \
    --ctx-size "$CONTEXT" \
    --n-gpu-layers 999 \
    --flash-attn on \
    --cache-type-k q8_0 \
    --cache-type-v q8_0 \
    --parallel 1 \
    --cont-batching \
    --jinja \
    --reasoning-preserve \
    --cors-origins localhost \
    --metrics \
    --no-webui
