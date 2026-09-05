"""Regression checks for config updates; never touch the real Codex home."""
from pathlib import Path
import os
import subprocess
import tempfile
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CodexDefaultsTest(unittest.TestCase):
    def run_apply(self, directory):
        return subprocess.run(
            ["bash", str(ROOT / "scripts/apply-codex-defaults.sh")],
            env={**os.environ, "CODEX_HOME": str(directory)},
            capture_output=True, text=True,
        )

    def test_profile_and_other_settings_survive_and_repeat_is_noop(self):
        original = ('notify = ["local-client", "turn-ended"]\n'
                    '[profiles.review]\nmodel = "review-model"\n'
                    'model_reasoning_effort = "low"\nservice_tier = "default"\n'
                    '[mcp_servers.example]\ncommand = "example"\n')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text(original)
            result = self.run_apply(directory)
            self.assertEqual(result.returncode, 0, result.stderr)
            actual = tomllib.loads(path.read_text())
            expected = tomllib.loads(original)
            expected.update(tomllib.loads((ROOT / "codex/defaults.toml").read_text()))
            self.assertEqual(actual, expected)
            self.assertEqual(actual["profiles"]["review"]["model"], "review-model")
            before = path.read_bytes()
            files = set(Path(directory).iterdir())
            self.assertEqual(self.run_apply(directory).returncode, 0)
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(set(Path(directory).iterdir()), files)
            backups = list(Path(directory).glob("config.toml.old.*"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_text(), original)

    def test_invalid_config_is_untouched(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text('model = "unterminated\n')
            before = path.read_bytes()
            self.assertNotEqual(self.run_apply(directory).returncode, 0)
            self.assertEqual(path.read_bytes(), before)

    def test_fresh_config(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_apply(directory)
            self.assertEqual(result.returncode, 0, result.stderr)
            path = Path(directory) / "config.toml"
            self.assertEqual(tomllib.loads(path.read_text()),
                             tomllib.loads((ROOT / "codex/defaults.toml").read_text()))
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_quoted_root_key_is_updated_without_duplicate(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text('"model" = "old"\n[profiles.review]\nmodel = "review"\n')
            result = self.run_apply(directory)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(tomllib.loads(path.read_text())["profiles"]["review"]["model"], "review")

    def test_multiline_managed_array(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text('project_doc_fallback_filenames = [\n "OLD.md",\n "README.md",\n]\n'
                            '[profiles.review]\nmodel = "review"\n')
            result = self.run_apply(directory)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = tomllib.loads(path.read_text())
            self.assertEqual(data["profiles"]["review"]["model"], "review")
            self.assertEqual(data["project_doc_fallback_filenames"],
                             tomllib.loads((ROOT / "codex/defaults.toml").read_text())["project_doc_fallback_filenames"])


if __name__ == "__main__":
    unittest.main()
