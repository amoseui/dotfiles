#!/usr/bin/env bash
# Parse the restricted key=value service config without executing shell code.
load_services_env() {
    local file=$1 line key value
    [ -f "$file" ] || return 0
    while IFS= read -r line || [ -n "$line" ]; do
        line=${line#"${line%%[![:space:]]*}"}
        line=${line%"${line##*[![:space:]]}"}
        [ -z "$line" ] && continue
        case "$line" in \#*) continue ;; esac
        case "$line" in
            *=*) ;;
            *) echo "Invalid service setting (expected KEY=VALUE): $line" >&2; return 1 ;;
        esac
        key=${line%%=*}
        value=${line#*=}
        key=${key%"${key##*[![:space:]]}"}
        value=${value#"${value%%[![:space:]]*}"}
        value=${value%"${value##*[![:space:]]}"}
        [[ "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || {
            echo "Invalid service setting name: $key" >&2
            return 1
        }
        case "$key" in
            HERMES_WEBUI_REPO|HERMES_WEBUI_PYTHON|HERMES_WEBUI_HOST|HERMES_WEBUI_PORT|PERSONAL_OBSERVATORY_REPO|PERSONAL_OBSERVATORY_HOST|PERSONAL_OBSERVATORY_PORT) ;;
            *) echo "Unsupported service setting: $key" >&2; return 1 ;;
        esac
        case "$value" in
            \"*\") value=${value#\"}; value=${value%\"} ;;
            \'*\') value=${value#\'}; value=${value%\'} ;;
        esac
        case "$value" in
            '$HOME'/*) value=$HOME/${value#'$HOME'/} ;;
            '~'/*) value=$HOME/${value#'~'/} ;;
        esac
        case "$value" in
            *'$('*|*'`'*|*'${'*) echo "Unsafe service setting value for $key" >&2; return 1 ;;
        esac
        export "$key=$value"
    done < "$file"
}
