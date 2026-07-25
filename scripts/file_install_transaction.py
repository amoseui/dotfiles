#!/usr/bin/env python3
"""Transactional installer for a JSON list of regular files."""

from __future__ import annotations

import argparse
import filecmp
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any


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


def atomic_copy(source: Path, destination: Path, mode: int) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{destination.name}.install-", dir=destination.parent)
    os.close(fd)
    temp = Path(name)
    try:
        shutil.copyfile(source, temp)
        temp.chmod(mode)
        with temp.open("rb") as handle:
            os.fsync(handle.fileno())
        os.replace(temp, destination)
    finally:
        temp.unlink(missing_ok=True)


def load_manifest(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if value.get("version") != 1 or not isinstance(value.get("entries"), list):
        raise SystemExit(f"Invalid file-install transaction manifest: {path}")
    return value


def rollback(path: Path) -> None:
    manifest = load_manifest(path)
    for entry in reversed(manifest["entries"]):
        if not entry.get("applied"):
            continue
        destination = Path(entry["destination"])
        old_kind = entry["old_kind"]
        if old_kind == "file":
            backup = Path(entry["backup"])
            if not backup.is_file():
                raise SystemExit(f"Cannot roll back; backup missing: {backup}")
            atomic_copy(backup, destination, int(entry["old_mode"]))
            backup.unlink()
        elif old_kind == "symlink":
            temp = destination.with_name(f".{destination.name}.rollback-link-{os.getpid()}")
            temp.unlink(missing_ok=True)
            os.symlink(entry["link_target"], temp)
            os.replace(temp, destination)
        elif old_kind == "missing":
            destination.unlink(missing_ok=True)
        else:
            raise SystemExit(f"Unknown rollback kind: {old_kind}")
    for raw_directory in reversed(manifest.get("created_directories", [])):
        try:
            Path(raw_directory).rmdir()
        except OSError:
            pass
    path.unlink()


def apply(spec_path: Path, manifest_path: Path, stamp: str) -> None:
    specs = json.loads(spec_path.read_text())
    if not isinstance(specs, list) or not specs:
        raise SystemExit("File-install transaction requires at least one spec")
    if manifest_path.exists() or manifest_path.is_symlink():
        raise SystemExit(f"Transaction manifest already exists: {manifest_path}")

    entries: list[dict[str, Any]] = []
    destinations: set[Path] = set()
    for spec in specs:
        source = Path(spec["source"])
        destination = Path(spec["destination"])
        mode = int(spec["mode"])
        if not source.is_file() or source.is_symlink():
            raise SystemExit(f"Refusing non-regular install source: {source}")
        if destination in destinations:
            raise SystemExit(f"Duplicate install destination: {destination}")
        destinations.add(destination)
        unchanged = (
            destination.is_file()
            and not destination.is_symlink()
            and filecmp.cmp(source, destination, shallow=False)
            and destination.stat().st_mode & 0o777 == mode
        )
        entry: dict[str, Any] = {
            "source": str(source),
            "destination": str(destination),
            "mode": mode,
            "applied": False,
            "unchanged": unchanged,
        }
        if unchanged:
            entry["old_kind"] = "unchanged"
        elif destination.is_symlink():
            entry.update(old_kind="symlink", link_target=os.readlink(destination))
        elif destination.exists():
            if not destination.is_file():
                raise SystemExit(f"Refusing non-file install destination: {destination}")
            backup = Path(f"{destination}.backup.{stamp}")
            if backup.exists() or backup.is_symlink():
                raise SystemExit(f"Install backup already exists: {backup}")
            entry.update(
                old_kind="file",
                backup=str(backup),
                old_mode=destination.stat().st_mode & 0o777,
            )
        else:
            entry["old_kind"] = "missing"
        entries.append(entry)

    planned_directories: list[Path] = []
    for destination in sorted(destinations, key=lambda item: len(item.parts)):
        missing = []
        parent = destination.parent
        while not parent.exists() and not parent.is_symlink():
            missing.append(parent)
            parent = parent.parent
        if not parent.is_dir() or parent.is_symlink():
            raise SystemExit(f"Install destination parent is not a regular directory: {parent}")
        for directory in reversed(missing):
            if directory not in planned_directories:
                planned_directories.append(directory)

    manifest = {"version": 1, "entries": entries, "created_directories": []}
    atomic_json(manifest_path, manifest)
    try:
        for directory in planned_directories:
            directory.mkdir()
            manifest["created_directories"].append(str(directory))
            atomic_json(manifest_path, manifest)
        for entry in entries:
            if entry["unchanged"]:
                continue
            destination = Path(entry["destination"])
            if entry["old_kind"] == "file":
                shutil.copy2(destination, entry["backup"])
            entry["applied"] = True
            atomic_json(manifest_path, manifest)
            atomic_copy(Path(entry["source"]), destination, int(entry["mode"]))
    except BaseException:
        rollback(manifest_path)
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="action", required=True)
    apply_parser = subparsers.add_parser("apply")
    apply_parser.add_argument("--spec", type=Path, required=True)
    apply_parser.add_argument("--manifest", type=Path, required=True)
    apply_parser.add_argument("--stamp", required=True)
    for action in ("rollback", "commit"):
        item = subparsers.add_parser(action)
        item.add_argument("manifest", type=Path)
    args = parser.parse_args()
    if args.action == "apply":
        apply(args.spec, args.manifest, args.stamp)
    elif args.action == "rollback":
        rollback(args.manifest)
    else:
        load_manifest(args.manifest)
        args.manifest.unlink()


if __name__ == "__main__":
    main()
