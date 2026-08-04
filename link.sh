#!/usr/bin/env bash
set -euo pipefail

DOTFILES_PATH=$(cd "$(dirname "$0")" && pwd)
STAMP=$(date +%Y%m%d%H%M%S)-$$

# Build and prepare the complete mapping before replacing any destination. The
# Python transaction restores files, directories, and symlinks on any failure.
python3 - "$DOTFILES_PATH" "$HOME" "$STAMP" <<'PY'
from pathlib import Path
import os, subprocess, sys

root, home = map(Path, sys.argv[1:3])
stamp = sys.argv[3]
hermes_live_root = home / ".hermes/skills"
hermes_backup_root = home / ".hermes/skill-backups"

files = (
    ("git/gitconfig", ".gitconfig"),
    ("git/gitignore", ".gitignore"),
    ("tmux/tmux.conf", ".tmux.conf"),
    ("vim/vimrc", ".vimrc"),
    ("zsh/zshrc", ".zshrc"),
    ("claude/settings.json", ".claude/settings.json"),
    ("claude/CLAUDE.md", ".claude/CLAUDE.md"),
    ("claude/statusline-command.sh", ".claude/statusline-command.sh"),
    # The common PKM rules have one source under shared/. Each platform gets a
    # stable adapter-facing link in its own skill root.
    ("shared/note-taking/CORE.md", ".claude/skills/note-taking-core.md"),
    ("shared/note-taking/CORE.md", ".hermes/skills/note-taking-core.md"),
    ("hermes/feed-pipeline", ".hermes/feed-pipeline"),
    ("ghostty/config", ".config/ghostty/config"),
    ("cmux/cmux.json", ".config/cmux/cmux.json"),
    ("herdr/config.toml", ".config/herdr/config.toml"),
)
directories = (
    ("claude/agents", ".claude/agents"),
    ("claude/commands", ".claude/commands"),
    ("claude/skills", ".claude/skills"),
    ("ghostty/themes", ".config/ghostty/themes"),
)

mappings = [(root / source, home / destination) for source, destination in files]

# Every non-ignored Hermes SKILL.md kept in dotfiles is linked automatically.
# Include untracked files as well: a newly added skill must be usable before
# the next commit, while ignored cache/config files must never become links.
hermes_skill_root = root / "hermes/skills"
tracked = subprocess.run(
    ["git", "-C", str(root), "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", "hermes/skills"],
    check=True,
    capture_output=True,
).stdout.split(b"\0")
hermes_skill_dirs = sorted({
    root / Path(os.fsdecode(raw)).parent
    for raw in tracked
    if raw and Path(os.fsdecode(raw)).name == "SKILL.md"
})
if not hermes_skill_dirs:
    raise SystemExit(f"Incomplete checkout; no Hermes skills under: {hermes_skill_root}")
for source_dir in hermes_skill_dirs:
    relative = source_dir.relative_to(root / "hermes/skills")
    mappings.append((source_dir, home / ".hermes/skills" / relative))

for source_name, destination_name in directories:
    source_dir = root / source_name
    if not source_dir.is_dir():
        raise SystemExit(f"Incomplete checkout; missing required directory: {source_dir}")
    for entry in source_dir.iterdir():
        if entry.name != ".gitkeep":
            mappings.append((entry, home / destination_name / entry.name))

for source, _ in mappings:
    if not source.exists():
        raise SystemExit(f"Incomplete checkout; missing required source: {source}")
if len({destination for _, destination in mappings}) != len(mappings):
    raise SystemExit("Duplicate dotfile destination in link transaction")

# Refuse destination-parent conflicts before creating directories or replacing
# any existing dotfile.
for _, destination in mappings:
    ancestor = destination.parent
    while not ancestor.exists() and not ancestor.is_symlink():
        ancestor = ancestor.parent
    if not ancestor.is_dir() or ancestor.is_symlink():
        raise SystemExit(f"Destination parent is not a regular directory: {ancestor}")

created_directories = []
prepared = []
states = []
success = False
try:
    parents = sorted({destination.parent for _, destination in mappings}, key=lambda path: len(path.parts))
    for parent in parents:
        missing = []
        cursor = parent
        while not cursor.exists():
            missing.append(cursor)
            cursor = cursor.parent
        for directory in reversed(missing):
            directory.mkdir()
            created_directories.append(directory)

    for index, (source, destination) in enumerate(mappings):
        if destination.is_symlink() and os.readlink(destination) == str(source):
            continue
        temp = destination.with_name(f".{destination.name}.link-new-{os.getpid()}-{index}")
        if temp.exists() or temp.is_symlink():
            raise RuntimeError(f"Temporary link path already exists: {temp}")
        os.symlink(source, temp)
        if destination.is_symlink():
            old_kind, old_value = "symlink", os.readlink(destination)
        elif destination.exists():
            old_kind = "entry"
            if destination.is_relative_to(hermes_live_root):
                relative = destination.relative_to(hermes_live_root)
                backup_parent = hermes_backup_root / relative.parent
                backup_parent.mkdir(parents=True, exist_ok=True)
                old_value = backup_parent / f"{relative.name}.{stamp}"
            else:
                old_value = Path(f"{destination}.old.{stamp}")
            if old_value.exists() or old_value.is_symlink():
                raise RuntimeError(f"Backup destination already exists: {old_value}")
        else:
            old_kind, old_value = "missing", None
        prepared.append((destination, temp, old_kind, old_value))

    for destination, temp, old_kind, old_value in prepared:
        state = [destination, old_kind, old_value, False, False]
        states.append(state)
        if old_kind == "entry":
            os.replace(destination, old_value)
            state[3] = True
        os.replace(temp, destination)
        state[4] = True
    success = True
except Exception:
    for destination, old_kind, old_value, backup_moved, published in reversed(states):
        if published:
            destination.unlink(missing_ok=True)
        if old_kind == "entry" and backup_moved:
            os.replace(old_value, destination)
        elif old_kind == "symlink" and published:
            os.symlink(old_value, destination)
    raise
finally:
    for _, temp, _, _ in prepared:
        temp.unlink(missing_ok=True)
    if not success:
        for directory in reversed(created_directories):
            try:
                directory.rmdir()
            except OSError:
                pass

for source, destination in mappings:
    if not destination.is_symlink() or os.readlink(destination) != str(source):
        raise SystemExit(f"Link verification failed: {destination}")
print(f"Dotfile links installed from {root}")
PY

if command -v vim >/dev/null 2>&1; then
    vim +silent! +PlugInstall +qall || true
fi