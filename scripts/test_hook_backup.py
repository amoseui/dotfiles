import copy
import importlib.util
from pathlib import Path
import unittest

HELPER = Path(__file__).with_name('canonicalize_herdr_hooks.py')


class HookBackupTests(unittest.TestCase):
    def module(self):
        self.assertTrue(HELPER.exists(), 'conservative hook canonicalizer must exist')
        spec = importlib.util.spec_from_file_location('canonicalize', HELPER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def hook(self, command=None, **extra):
        return {'type': 'command', 'command': command or 'if [ -x "$HOME/.claude/hooks/herdr-agent-state.sh" ]; then bash "$HOME/.claude/hooks/herdr-agent-state.sh" session; fi', 'timeout': 10, **extra}

    def test_dedup_preserves_unrelated_hooks_order_and_settings(self):
        m = self.module()
        portable = self.hook()
        native = self.hook("bash '/Users/synthetic/.claude/hooks/herdr-agent-state.sh' session")
        unrelated = self.hook('echo unrelated')
        raw = {'model': 'retained', 'hooks': {'SessionStart': [
            {'matcher': '*', 'hooks': [portable, unrelated]},
            {'matcher': '^(startup|resume|clear|compact|fork)$', 'hooks': [native]},
            {'matcher': 'other', 'hooks': [native]}], 'Stop': [{'hooks': [unrelated]}]}}
        original = copy.deepcopy(raw)
        clean = m.canonicalize(raw, 'claude', Path('/Users/synthetic'))
        self.assertEqual(raw, original)
        self.assertEqual(clean['model'], 'retained')
        self.assertEqual(clean['hooks']['Stop'], raw['hooks']['Stop'])
        self.assertEqual(clean['hooks']['SessionStart'], [raw['hooks']['SessionStart'][0], raw['hooks']['SessionStart'][2]])
        self.assertEqual(m.canonicalize(clean, 'claude', Path('/Users/synthetic')), clean)

    def test_custom_scope_timeout_and_extra_shell_actions_never_discarded(self):
        m = self.module()
        hooks = [self.hook(), self.hook(timeout=20), self.hook('bash "$HOME/.claude/hooks/herdr-agent-state.sh" session; echo extra')]
        raw = {'hooks': {'SessionStart': [{'matcher': '*', 'hooks': hooks}, {'matcher': 'custom', 'hooks': [self.hook()]}]}}
        self.assertEqual(m.canonicalize(raw, 'claude', Path('/Users/synthetic')), raw)

    def test_codex_native_and_portable_dedup_and_backup_trust_omission(self):
        m = self.module()
        native = self.hook('bash /Users/synthetic/.codex/herdr-agent-state.sh session')
        raw = {'hooks': {'SessionStart': [{'hooks': [native]}, {'matcher': '^(startup|resume|clear|compact|fork)$', 'hooks': [native]}]}, 'hookTrustHash': 'machine-local'}
        clean = m.canonicalize(raw, 'codex', Path('/Users/synthetic'))
        self.assertNotIn('hookTrustHash', clean)
        self.assertEqual(len(clean['hooks']['SessionStart']), 1)
        self.assertIn('$HOME/.codex/', clean['hooks']['SessionStart'][0]['hooks'][0]['command'])

class ManagedHookIntegrationTests(unittest.TestCase):
    def test_actual_managed_scripts_emit_one_report_after_canonicalization(self):
        import contextlib
        import json
        import os
        import shutil
        import socket
        import subprocess
        import tempfile
        import threading

        spec = importlib.util.spec_from_file_location('canonicalize_integration', HELPER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        root = HELPER.resolve().parents[1]
        with tempfile.TemporaryDirectory(prefix='.hook-fixture-', dir=root) as raw:
            home = Path(raw)
            for platform in ('claude', 'codex'):
                with self.subTest(platform=platform):
                    suffix = '.claude/hooks/herdr-agent-state.sh' if platform == 'claude' else '.codex/herdr-agent-state.sh'
                    target = home / suffix
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(root / platform / 'hooks/herdr-agent-state.sh', target)
                    target.chmod(0o755)
                    portable = {'type': 'command', 'command': module.command_for(platform), 'timeout': 10}
                    native = {**portable, 'command': f"bash '{target}' session"}
                    original = {'hooks': {'SessionStart': [
                        {'matcher': '*', 'hooks': [portable]},
                        {'matcher': '^(startup|resume|clear|compact|fork)$', 'hooks': [native]}]}}
                    canonical = module.canonicalize(original, platform, home)
                    # A relative socket path keeps macOS sun_path under 104 bytes.
                    reports, failures = [], []
                    stopped = threading.Event()
                    with contextlib.chdir(home), socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
                        try:
                            server.bind('hook.sock')
                        except PermissionError:
                            self.skipTest('sandbox denies local AF_UNIX bind; rerun in a socket-enabled environment')
                        server.listen()
                        server.settimeout(0.1)
                        def serve():
                            try:
                                while not stopped.is_set():
                                    try:
                                        client, _ = server.accept()
                                    except TimeoutError:
                                        continue
                                    with client:
                                        client.settimeout(1)
                                        payload = b''
                                        while not payload.endswith(b'\n'):
                                            chunk = client.recv(65536)
                                            if not chunk:
                                                break
                                            payload += chunk
                                        reports.append(json.loads(payload))
                                        client.sendall(b'{"ok": true}\n')
                            except Exception as error:
                                failures.append(type(error).__name__)
                        worker = threading.Thread(target=serve)
                        worker.start()
                        try:
                            env = {'PATH': '/opt/homebrew/bin:/usr/bin:/bin', 'HOME': str(home), 'TMPDIR': str(home),
                                   'HERDR_ENV': '1', 'HERDR_SOCKET_PATH': 'hook.sock', 'HERDR_PANE_ID': 'synthetic:p1'}
                            session = json.dumps({'hook_event_name': 'SessionStart', 'session_id': 'synthetic-session',
                                                  'transcript_path': str(home / 'synthetic.jsonl'), 'source': 'startup'})
                            for group in canonical['hooks']['SessionStart']:
                                for hook in group['hooks']:
                                    result = subprocess.run(['bash', '-c', hook['command']], input=session,
                                                            text=True, capture_output=True, env=env, timeout=5)
                                    self.assertEqual(result.returncode, 0, result.stderr)
                        finally:
                            stopped.set()
                            worker.join(timeout=2)
                        self.assertFalse(worker.is_alive())
                        self.assertEqual(failures, [])
                        self.assertEqual(len(reports), 1)
                        self.assertEqual(reports[0]['method'], 'pane.report_agent_session')
                        self.assertEqual(reports[0]['params']['agent_session_id'], 'synthetic-session')
                        self.assertEqual(reports[0]['params']['agent'], platform)
                    (home / 'hook.sock').unlink()


if __name__ == '__main__':
    unittest.main()
