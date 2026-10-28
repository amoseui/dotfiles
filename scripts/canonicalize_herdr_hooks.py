#!/usr/bin/env python3
"""Conservatively canonicalize a backup JSON; output is explicit, never in-place."""
import argparse
import copy
import json
from pathlib import Path
import tempfile
import os

SCOPES = {None, '*', '^(startup|resume|clear|compact|fork)$'}
NARROW = '^(startup|resume|clear|compact|fork)$'


def command_for(platform):
    suffix = '.claude/hooks/herdr-agent-state.sh' if platform == 'claude' else '.codex/herdr-agent-state.sh'
    return f'if [ -x "$HOME/{suffix}" ]; then bash "$HOME/{suffix}" session; fi'


def recognized(command, platform, source_home):
    suffix = '.claude/hooks/herdr-agent-state.sh' if platform == 'claude' else '.codex/herdr-agent-state.sh'
    paths = ['$HOME/' + suffix, '~/' + suffix, str(source_home / suffix)]
    known = {command_for(platform), f"bash '{source_home / suffix}' session"}
    for path in paths:
        # Exact known command forms only. Do not parse or execute arbitrary shell.
        known.update({f'bash {path} session', f'bash "{path}" session',
                      f'if [ -x "{path}" ]; then bash "{path}" session; fi'})
    return command in known


def canonicalize(value, platform, source_home):
    if platform not in {'claude', 'codex'} or not isinstance(value, dict):
        raise ValueError('Expected Claude/Codex settings object')
    clean = copy.deepcopy(value)
    for key in ('hookTrustHash', 'hook_trust_hash'):
        clean.pop(key, None)
    groups = clean.get('hooks', {}).get('SessionStart')
    if not isinstance(groups, list):
        return clean
    broad = set()
    for group in groups:
        if not isinstance(group, dict) or group.get('matcher') not in {None, '*'} or set(group) - {'matcher', 'hooks'}:
            continue
        for hook in group.get('hooks', []):
            if hook.get('type') == 'command' and recognized(hook.get('command'), platform, source_home):
                signature = {**hook, 'command': command_for(platform)}
                broad.add(json.dumps(signature, sort_keys=True))
    seen = set()
    output = []
    for group in groups:
        if not isinstance(group, dict) or group.get('matcher') not in SCOPES or set(group) - {'matcher', 'hooks'}:
            output.append(group)
            continue
        hooks = []
        for hook in group.get('hooks', []):
            if hook.get('type') != 'command' or not recognized(hook.get('command'), platform, source_home):
                hooks.append(hook)
                continue
            canonical = {**hook, 'command': command_for(platform)}
            signature = json.dumps(canonical, sort_keys=True)
            scope = group.get('matcher')
            if scope == NARROW and signature in broad:
                continue
            scope_key = 'broad' if scope in {None, '*'} else scope
            key = (scope_key, signature)
            if key in seen:
                continue
            seen.add(key)
            hooks.append(canonical)
        if hooks or not group.get('hooks'):
            output.append({**group, 'hooks': hooks})
    clean['hooks']['SessionStart'] = output
    return clean


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--platform', choices=('claude', 'codex'), required=True)
    parser.add_argument('--source-home', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    value = json.loads(args.input.read_text())
    clean = canonicalize(value, args.platform, args.source_home)
    if args.output:
        if args.output.resolve() == args.input.resolve() or args.output.is_symlink():
            parser.error('Output must be a separate regular backup file')
        fd, raw = tempfile.mkstemp(prefix='.hooks-backup-', dir=args.output.parent)
        try:
            with os.fdopen(fd, 'w') as handle:
                json.dump(clean, handle, indent=2, ensure_ascii=False)
                handle.write('\n')
            os.chmod(raw, 0o644)
            os.replace(raw, args.output)
        finally:
            Path(raw).unlink(missing_ok=True)
    print(json.dumps({'changed': clean != value, 'written': bool(args.output)}))


if __name__ == '__main__':
    main()
