#!/usr/bin/env python3
"""Transactional installer for Hermes files that are rewritten at runtime."""

from __future__ import annotations

import argparse
import filecmp
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any

FILES = (
    ("hermes/config.yaml", "config.yaml", 0o600),
    ("hermes/SOUL.md", "SOUL.md", 0o600),
    ("hermes/cron/jobs.json", "cron/jobs.json", 0o600),
    ("hermes/scripts/chromium_docs_check.py", "scripts/chromium_docs_check.py", 0o755),
)


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.new-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(name, 0o600)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def atomic_copy(src: Path, dst: Path, mode: int) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{dst.name}.new-", dir=dst.parent)
    os.close(fd)
    temp = Path(name)
    try:
        shutil.copyfile(src, temp)
        os.chmod(temp, mode)
        with temp.open("rb") as handle:
            os.fsync(handle.fileno())
        os.replace(temp, dst)
    finally:
        temp.unlink(missing_ok=True)


def load_manifest(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if value.get("version") != 1 or not isinstance(value.get("entries"), list):
        raise SystemExit(f"Invalid restore transaction manifest: {path}")
    return value


def rollback(path: Path) -> None:
    manifest = load_manifest(path)
    for entry in reversed(manifest["entries"]):
        if not entry.get("applied"):
            continue
        dst = Path(entry["destination"])
        old_kind = entry["old_kind"]
        if old_kind == "file":
            backup = Path(entry["backup"])
            if not backup.is_file():
                raise SystemExit(f"Cannot roll back; backup missing: {backup}")
            atomic_copy(backup, dst, int(entry["old_mode"]))
        elif old_kind == "symlink":
            temp = dst.with_name(f".{dst.name}.rollback-link-{os.getpid()}")
            temp.unlink(missing_ok=True)
            os.symlink(entry["link_target"], temp)
            os.replace(temp, dst)
        elif old_kind == "missing":
            dst.unlink(missing_ok=True)
        else:
            raise SystemExit(f"Unknown rollback kind: {old_kind}")
    path.unlink()


def apply(root: Path, hermes_home: Path, stamp: str) -> Path:
    stale = sorted(hermes_home.glob(".restore-transaction-*.json"))
    if stale:
        raise SystemExit(
            "Unfinished Hermes restore transaction found. Roll it back first:\n  "
            + "\n  ".join(str(item) for item in stale)
        )

    manifest_path = hermes_home / f".restore-transaction-{stamp}.json"
    entries: list[dict[str, Any]] = []
    for src_rel, dst_rel, mode in FILES:
        src, dst = root / src_rel, hermes_home / dst_rel
        if not src.is_file():
            raise SystemExit(f"Missing restore source: {src}")
        unchanged = (
            dst.is_file()
            and not dst.is_symlink()
            and filecmp.cmp(src, dst, shallow=False)
            and (dst.stat().st_mode & 0o777) == mode
        )
        entry: dict[str, Any] = {
            "source": str(src),
            "destination": str(dst),
            "mode": mode,
            "applied": False,
            "unchanged": unchanged,
        }
        if unchanged:
            entry["old_kind"] = "unchanged"
            entries.append(entry)
            continue
        if dst.is_symlink():
            entry.update(old_kind="symlink", link_target=os.readlink(dst))
        elif dst.exists():
            if not dst.is_file():
                raise SystemExit(f"Refusing to replace non-file destination: {dst}")
            backup = Path(f"{dst}.backup.{stamp}")
            if backup.exists() or backup.is_symlink():
                raise SystemExit(f"Backup already exists: {backup}")
            entry.update(
                old_kind="file",
                backup=str(backup),
                old_mode=dst.stat().st_mode & 0o777,
            )
        else:
            entry.update(old_kind="missing")
        entries.append(entry)

    manifest = {"version": 1, "entries": entries}
    atomic_json(manifest_path, manifest)
    try:
        for entry in entries:
            if entry["unchanged"]:
                continue
            dst = Path(entry["destination"])
            if entry["old_kind"] == "file":
                backup = Path(entry["backup"])
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(dst, backup)
            # Mark before replacement so a process interruption never leaves a
            # changed target that the persisted manifest considers untouched.
            entry["applied"] = True
            atomic_json(manifest_path, manifest)
            atomic_copy(Path(entry["source"]), dst, int(entry["mode"]))
    except BaseException:
        rollback(manifest_path)
        raise
    return manifest_path


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="action", required=True)
    apply_parser = sub.add_parser("apply")
    apply_parser.add_argument("--root", type=Path, required=True)
    apply_parser.add_argument("--hermes-home", type=Path, required=True)
    apply_parser.add_argument("--stamp", required=True)
    for action in ("rollback", "commit"):
        item = sub.add_parser(action)
        item.add_argument("manifest", type=Path)
    args = parser.parse_args()

    if args.action == "apply":
        print(apply(args.root, args.hermes_home, args.stamp))
    elif args.action == "rollback":
        rollback(args.manifest)
    else:
        load_manifest(args.manifest)
        args.manifest.unlink()


if __name__ == "__main__":
    main()
