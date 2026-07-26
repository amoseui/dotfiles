#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
HERMES_HOME_DIR=${HERMES_HOME:-$HOME/.hermes}
BREW=/opt/homebrew/bin/brew
HERMES_PY="$HERMES_HOME_DIR/hermes-agent/venv/bin/python"
PERSONAL_OBSERVATORY_REPO=${PERSONAL_OBSERVATORY_REPO:-$HOME/Workspace/personal-observatory}
TMP_BREW=""
STAGE_DIR=""

cleanup() {
    [ -n "$TMP_BREW" ] && rm -f "$TMP_BREW"
    if [ -n "$STAGE_DIR" ] && [ -d "$STAGE_DIR" ]; then
        rm -f \
            "$STAGE_DIR/Brewfile" \
            "$STAGE_DIR/hermes/config.yaml" \
            "$STAGE_DIR/hermes/SOUL.md" \
            "$STAGE_DIR/hermes/cron/jobs.json" \
            "$STAGE_DIR/hermes/scripts/chromium_docs_check.py" \
            "$STAGE_DIR/karabiner/karabiner.json" \
            "$STAGE_DIR/services/personal-observatory/config.local.yaml"
        rmdir "$STAGE_DIR/hermes/cron" "$STAGE_DIR/hermes/scripts" \
            "$STAGE_DIR/hermes" "$STAGE_DIR/karabiner" \
            "$STAGE_DIR/services/personal-observatory" "$STAGE_DIR/services" \
            "$STAGE_DIR" 2>/dev/null || true
    fi
}
trap cleanup EXIT

require_file() {
    [ -f "$1" ] || { printf 'Missing required file: %s\n' "$1" >&2; exit 1; }
}

[ -x "$BREW" ] || { echo "Apple Silicon Homebrew not found at $BREW" >&2; exit 1; }
[ -x "$HERMES_PY" ] || { echo "Hermes Python not found at $HERMES_PY" >&2; exit 1; }

require_file "$HERMES_HOME_DIR/config.yaml"
require_file "$HERMES_HOME_DIR/SOUL.md"
require_file "$HERMES_HOME_DIR/cron/jobs.json"
require_file "$HERMES_HOME_DIR/scripts/chromium_docs_check.py"
require_file "$HOME/.config/karabiner/karabiner.json"
require_file "$PERSONAL_OBSERVATORY_REPO/config.local.yaml"

STAGE_DIR=$(mktemp -d "${TMPDIR:-/tmp}/dotfiles-sync.XXXXXX")
chmod 700 "$STAGE_DIR"
mkdir -p "$STAGE_DIR/hermes/cron" "$STAGE_DIR/hermes/scripts" \
    "$STAGE_DIR/karabiner" "$STAGE_DIR/services/personal-observatory"

TMP_BREW=$(mktemp)
HOMEBREW_NO_AUTO_UPDATE=1 "$BREW" bundle dump --force --file="$TMP_BREW"
python3 - "$TMP_BREW" "$STAGE_DIR/Brewfile" <<'PY'
from pathlib import Path
import sys
src, dst = map(Path, sys.argv[1:])
lines = [line for line in src.read_text().splitlines()
         if line.strip() != 'tap "adoptopenjdk/openjdk"']
if 'brew "antigen"' not in lines:
    insert_at = next((i for i, line in enumerate(lines) if not line.startswith("tap ")), len(lines))
    lines.insert(insert_at, 'brew "antigen"')

# These GUI apps are currently installed outside Homebrew, but have verified
# official Homebrew Casks. Keep them in the portable snapshot so the new Mac
# installs and subsequently manages them through Homebrew.
migration_casks = (
    "claude", "clockify", "cmux", "cursor", "discord", "figma", "firefox",
    "google-chrome", "google-drive", "iterm2", "jetbrains-toolbox",
    "karabiner-elements", "notion", "obsidian", "reader", "readdle-spark",
    "rectangle", "slack", "tailscale-app", "todoist-app",
    "visual-studio-code", "zoom",
)
existing_casks = {
    line.split('"', 2)[1] for line in lines
    if line.startswith('cask "') and line.count('"') >= 2
}
insert_at = next(
    (i for i, line in enumerate(lines) if line.startswith(("mas ", "vscode "))),
    len(lines),
)
for token in migration_casks:
    if token not in existing_casks:
        lines.insert(insert_at, f'cask "{token}"')
        insert_at += 1
dst.write_text("\n".join(lines) + "\n")
PY

HERMES_REDACT_SECRETS=true "$HERMES_PY" - "$HERMES_HOME_DIR" "$STAGE_DIR" <<'PY'
from pathlib import Path
import json, re, sys, yaml
from agent.redact import redact_sensitive_text

home, root = map(Path, sys.argv[1:])
config = yaml.safe_load((home / "config.yaml").read_text()) or {}
# Approval history is machine-local state, not portable configuration.
config.pop("command_allowlist", None)

# Fail closed on future config additions: only persist reviewed, portable sections.
safe_sections = (
    "model", "agent", "terminal", "web", "browser", "auxiliary", "display",
    "dashboard", "tts", "skills", "onboarding", "_config_version", "plugins",
    "session_reset", "image_gen", "platform_toolsets", "known_plugin_toolsets",
    "timezone", "security", "privacy", "approvals",
)
portable_config = {key: config[key] for key in safe_sections if key in config}

# MCP executable shape is portable; all MCP env values are secrets by default.
sensitive_values = []
portable_mcp = {}
def env_name(key):
    name = re.sub(r"[^A-Z0-9_]", "_", str(key).upper())
    return "_" + name if not name or name[0].isdigit() else name

for name, server in (config.get("mcp_servers") or {}).items():
    if not isinstance(server, dict):
        continue
    clean_server = {
        key: server[key]
        for key in ("command", "args", "enabled", "transport", "timeout")
        if key in server
    }
    if isinstance(server.get("env"), dict):
        sensitive_values.extend(
            value for value in server["env"].values()
            if isinstance(value, str) and value and not value.startswith("${")
        )
        clean_server["env"] = {
            str(key): (
                value if isinstance(value, str) and value.startswith("${") and value.endswith("}")
                else "${" + env_name(key) + "}"
            )
            for key, value in server["env"].items()
        }
    portable_mcp[name] = clean_server
if portable_mcp:
    portable_config["mcp_servers"] = portable_mcp
config = portable_config

sensitive_key = re.compile(
    r"(?:token|secret|password|passwd|api[_-]?key|private[_-]?key|credential|authorization|cookie|headers?|auth)$",
    re.I,
)

def sanitize(value):
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if isinstance(item, str) and item and sensitive_key.search(str(key)):
                if item.startswith("${") and item.endswith("}"):
                    result[key] = item
                else:
                    sensitive_values.append(item)
                    result[key] = "${" + env_name(key) + "}"
            else:
                result[key] = sanitize(item)
        return result
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    return value

config = sanitize(config)
config_text = yaml.safe_dump(config, sort_keys=False, allow_unicode=True)
if any(secret in config_text for secret in sensitive_values):
    raise SystemExit("Refusing to write: config secret sanitization failed")
(root / "hermes/config.yaml").write_text(config_text)

raw = json.loads((home / "cron/jobs.json").read_text())
jobs = raw.get("jobs", raw)
keep = {
    "id", "name", "prompt", "schedule", "provider", "model", "base_url",
    "skills", "skill", "deliver", "origin", "repeat", "no_agent", "script",
    "context_from", "enabled_toolsets", "workdir", "enabled",
}
clean = [{key: job[key] for key in job if key in keep and job[key] is not None}
         for job in jobs]

# Keep job definitions, not machine-local execution counters or descriptive
# Discord account metadata. Routing IDs remain because delivery depends on them.
for job in clean:
    repeat = job.get("repeat")
    if isinstance(repeat, dict):
        times = repeat.get("times")
        if times is None:
            job.pop("repeat", None)
        else:
            job["repeat"] = {"times": times, "completed": 0}
    origin = job.get("origin")
    if isinstance(origin, dict):
        job["origin"] = {
            key: origin[key]
            for key in ("platform", "chat_id", "thread_id")
            if key in origin
        }
    prompt = job.get("prompt")
    if isinstance(prompt, str) and "/tmp/" in prompt:
        temporary_names = sorted(set(re.findall(r"/tmp/([A-Za-z0-9._-]+)", prompt)))
        if temporary_names:
            for temporary_name in temporary_names:
                prompt = prompt.replace(f"/tmp/{temporary_name}", f"$WORKDIR/{temporary_name}")
            cleanup = " ".join(f'"$WORKDIR/{name}"' for name in temporary_names)
            setup = (
                'WORKDIR=$(mktemp -d "${TMPDIR:-/tmp}/hermes-cron.XXXXXX")\n'
                f"trap 'rm -f {cleanup}; rmdir \"$WORKDIR\"' EXIT\n"
            )
            if "```\n" not in prompt:
                raise SystemExit(f"Refusing to rewrite temporary paths outside a code block: {job.get('id')}")
            job["prompt"] = prompt.replace("```\n", "```\n" + setup, 1)

def portable(value):
    if isinstance(value, str):
        return value.replace(str(Path.home()), "~")
    if isinstance(value, list):
        return [portable(item) for item in value]
    if isinstance(value, dict):
        return {key: portable(item) for key, item in value.items()}
    return value

clean = [portable(job) for job in clean]
(root / "hermes/cron/jobs.json").write_text(
    json.dumps({"jobs": clean}, ensure_ascii=False, indent=2) + "\n"
)

# Validate the generated artifacts without exposing values.
yaml.safe_load((root / "hermes/config.yaml").read_text())
json.loads((root / "hermes/cron/jobs.json").read_text())
todoist_env = (((config.get("mcp_servers") or {}).get("todoist") or {}).get("env") or {})
if todoist_env.get("TODOIST_API_TOKEN") != "${TODOIST_API_TOKEN}":
    raise SystemExit("Refusing to write a non-placeholder Todoist token")
for path in (root / "hermes/config.yaml", root / "hermes/cron/jobs.json"):
    text = path.read_text()
    if any(secret in text for secret in sensitive_values):
        raise SystemExit(f"Refusing to write a known config secret to {path.name}")
    parsed = yaml.safe_load(text) if path.suffix == ".yaml" else json.loads(text)
    def neutralize_placeholders(value):
        if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            return ""
        if isinstance(value, list):
            return [neutralize_placeholders(item) for item in value]
        if isinstance(value, dict):
            return {key: neutralize_placeholders(item) for key, item in value.items()}
        return value
    redactable = yaml.safe_dump(neutralize_placeholders(parsed), allow_unicode=True)
    if redact_sensitive_text(redactable) != redactable:
        raise SystemExit(f"Hermes secret redactor found potential plaintext credentials in {path.name}")
    if re.search(r"-----BEGIN .*PRIVATE KEY-----|(?:ghp|github_pat|sk-ant|sk-proj)-[A-Za-z0-9_-]{12,}", text):
        raise SystemExit(f"Potential secret detected in {path}")
PY

install -m 600 "$HERMES_HOME_DIR/SOUL.md" "$STAGE_DIR/hermes/SOUL.md"
python3 - "$HERMES_HOME_DIR/scripts/chromium_docs_check.py" "$STAGE_DIR/hermes/scripts/chromium_docs_check.py" <<'PY'
from pathlib import Path
import sys
src, dst = map(Path, sys.argv[1:])
text = src.read_text().replace(
    f"VAULT=Path({str(Path.home() / 'Obsidian/amoseui')!r})",
    "VAULT=Path.home()/'Obsidian/amoseui'",
)
dst.write_text(text)
PY
chmod 700 "$STAGE_DIR/hermes/scripts/chromium_docs_check.py"
install -m 600 "$HOME/.config/karabiner/karabiner.json" "$STAGE_DIR/karabiner/karabiner.json"

HERMES_REDACT_SECRETS=true "$HERMES_PY" - \
    "$PERSONAL_OBSERVATORY_REPO/config.local.yaml" \
    "$STAGE_DIR/services/personal-observatory/config.local.yaml" <<'PY'
from pathlib import Path
import sys, yaml
from agent.redact import redact_sensitive_text

src, dst = map(Path, sys.argv[1:])
raw = yaml.safe_load(src.read_text()) or {}
allowed = ("server", "obsidian", "hermes", "feeds", "usage", "calendar")
config = {key: raw[key] for key in allowed if key in raw}
# Defense in depth: the wrapper also rejects non-loopback binds, but the
# portable app config itself should be safe when launched manually.
server = dict(config.get("server") or {})
server["host"] = "127.0.0.1"
config["server"] = server

def portable(value):
    if isinstance(value, str):
        return value.replace(str(Path.home()), "~")
    if isinstance(value, list):
        return [portable(item) for item in value]
    if isinstance(value, dict):
        return {key: portable(item) for key, item in value.items()}
    return value

text = yaml.safe_dump(portable(config), sort_keys=False, allow_unicode=True)
redactable_config = portable(config)
def neutralize_placeholders(value):
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        return ""
    if isinstance(value, list):
        return [neutralize_placeholders(item) for item in value]
    if isinstance(value, dict):
        return {key: neutralize_placeholders(item) for key, item in value.items()}
    return value
redactable = yaml.safe_dump(neutralize_placeholders(redactable_config), allow_unicode=True)
if redact_sensitive_text(redactable) != redactable:
    raise SystemExit("Refusing to write potential credentials from Personal Observatory config")
dst.write_text(text)
PY

# Nothing reaches the worktree until every staged artifact parses and passes
# both Hermes' redactor and broad credential-pattern checks.
HERMES_REDACT_SECRETS=true "$HERMES_PY" - "$STAGE_DIR" <<'PY'
from pathlib import Path
import json, re, sys, yaml
from agent.redact import redact_sensitive_text

stage = Path(sys.argv[1])
files = (
    "Brewfile",
    "hermes/config.yaml",
    "hermes/SOUL.md",
    "hermes/cron/jobs.json",
    "hermes/scripts/chromium_docs_check.py",
    "karabiner/karabiner.json",
    "services/personal-observatory/config.local.yaml",
)
patterns = (
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"),
    re.compile(r"(?i)\b(?:bearer\s+)[A-Za-z0-9._~+/-]{16,}"),
    re.compile(r"\b(?:ghp|github_pat|sk-ant|sk-proj|sk)-[A-Za-z0-9_-]{12,}"),
    re.compile(r"\bya29\.[A-Za-z0-9_-]{20,}"),
    re.compile(r"\bmfa\.[A-Za-z0-9_-]{20,}"),
    re.compile(r"\b[A-Za-z0-9_-]{23,}\.[A-Za-z0-9_-]{6}\.[A-Za-z0-9_-]{20,}\b"),
    re.compile(
        r"(?im)^\s*(?:token|secret|password|passwd|api[_-]?key|private[_-]?key|"
        r"credential|authorization|cookie)\s*[:=]\s*(?!\$\{)[\"']?[^\s#\"']{12,}"
    ),
    re.compile(
        r"(?i)(?<![A-Za-z0-9_])(?:token|secret|password|passwd|api[_-]?key|"
        r"private[_-]?key|credential|authorization|cookie)\s*[:=]\s*"
        r"(?!\$\{)[\"']?[^\s&#,\"'\]}]{8,}"
    ),
    re.compile(r"(?i)https?://[^/\s:@]+:[^@\s/]+@"),
)
for rel in files:
    path = stage / rel
    if not path.is_file():
        raise SystemExit(f"Missing staged artifact: {rel}")
    text = path.read_text()
    redactable = text
    if rel.endswith((".yaml", ".json")):
        parsed = yaml.safe_load(text) if rel.endswith(".yaml") else json.loads(text)
        def neutralize_placeholders(value):
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                return ""
            if isinstance(value, list):
                return [neutralize_placeholders(item) for item in value]
            if isinstance(value, dict):
                return {key: neutralize_placeholders(item) for key, item in value.items()}
            return value
        redactable = yaml.safe_dump(neutralize_placeholders(parsed), allow_unicode=True)
    if redact_sensitive_text(redactable) != redactable or any(pattern.search(text) for pattern in patterns):
        raise SystemExit(f"Potential plaintext credential in staged artifact: {rel}")

yaml.safe_load((stage / "hermes/config.yaml").read_text())
yaml.safe_load((stage / "services/personal-observatory/config.local.yaml").read_text())
json.loads((stage / "hermes/cron/jobs.json").read_text())
json.loads((stage / "karabiner/karabiner.json").read_text())
compile((stage / "hermes/scripts/chromium_docs_check.py").read_text(), "chromium_docs_check.py", "exec")
PY

# Prepare all replacement files before touching the worktree, then replace each
# target atomically. Normal failures roll the complete set back.
python3 - "$STAGE_DIR" "$ROOT" <<'PY'
from pathlib import Path
import filecmp, os, shutil, sys, tempfile

stage, root = map(Path, sys.argv[1:])
files = (
    ("Brewfile", 0o644),
    ("hermes/config.yaml", 0o644),
    ("hermes/SOUL.md", 0o644),
    ("hermes/cron/jobs.json", 0o644),
    ("hermes/scripts/chromium_docs_check.py", 0o755),
    ("karabiner/karabiner.json", 0o644),
    ("services/personal-observatory/config.local.yaml", 0o644),
)
prepared = []
changed = []
success = False
rollback_complete = False
try:
    for rel, mode in files:
        src, dst = stage / rel, root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if (
            dst.is_file()
            and not dst.is_symlink()
            and filecmp.cmp(src, dst, shallow=False)
            and (dst.stat().st_mode & 0o777) == mode
        ):
            continue
        if dst.exists() and not dst.is_symlink() and not dst.is_file():
            raise RuntimeError(f"Refusing to replace non-file destination: {dst}")
        tmp = None
        rollback = None
        old_kind = "missing"
        try:
            fd, tmp_name = tempfile.mkstemp(prefix=f".{dst.name}.sync-new-", dir=dst.parent)
            os.close(fd)
            tmp = Path(tmp_name)
            shutil.copyfile(src, tmp)
            os.chmod(tmp, mode)
            with tmp.open("rb") as handle:
                os.fsync(handle.fileno())
            if dst.is_symlink():
                old_kind = "symlink"
                rollback = os.readlink(dst)
            elif dst.exists():
                old_kind = "file"
                fd, old_name = tempfile.mkstemp(prefix=f".{dst.name}.sync-old-", dir=dst.parent)
                os.close(fd)
                rollback = Path(old_name)
                shutil.copy2(dst, rollback)
            prepared.append((dst, tmp, old_kind, rollback))
        except Exception:
            if isinstance(tmp, Path):
                tmp.unlink(missing_ok=True)
            if isinstance(rollback, Path):
                rollback.unlink(missing_ok=True)
            raise

    for dst, tmp, old_kind, rollback in prepared:
        os.replace(tmp, dst)
        changed.append((dst, old_kind, rollback))
    success = True
except Exception as original_error:
    try:
        for dst, old_kind, rollback in reversed(changed):
            if old_kind == "file" and isinstance(rollback, Path) and rollback.exists():
                os.replace(rollback, dst)
            elif old_kind == "symlink" and isinstance(rollback, str):
                temp_link = dst.with_name(f".{dst.name}.sync-link-{os.getpid()}")
                temp_link.unlink(missing_ok=True)
                os.symlink(rollback, temp_link)
                os.replace(temp_link, dst)
            elif old_kind == "missing":
                dst.unlink(missing_ok=True)
        rollback_complete = True
    except Exception as rollback_error:
        raise RuntimeError(
            "Backup publish failed and automatic rollback was incomplete; "
            "preserved .sync-old-* files require manual recovery"
        ) from rollback_error
    raise
finally:
    for _, tmp, old_kind, rollback in prepared:
        tmp.unlink(missing_ok=True)
        if (success or rollback_complete) and old_kind == "file" and isinstance(rollback, Path):
            try:
                rollback.unlink(missing_ok=True)
            except OSError as cleanup_error:
                print(f"Warning: could not remove temporary rollback file: {cleanup_error}", file=sys.stderr)
PY

printf 'Refreshed reproducible Mac settings in %s\n' "$ROOT"
printf 'Review with: git diff -- Brewfile hermes karabiner services\n'
