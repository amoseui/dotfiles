"""Public sync contract checks; fixtures never inspect or alter the real home.

These checks cover executable examples, portable references, and concrete public
boundary violations. They do not certify agent behavior or replace independent
review of authorization, risk classification, or the private extension.
"""
from pathlib import Path
import os
import re
import subprocess
import tempfile
import unittest


SKILL_DIR = Path(__file__).resolve().parents[1]
ROOT = SKILL_DIR.parents[2]
OPTIONAL_EXTENSION = "private/docs/DOTFILES-SYNC.md"
MACHINE_HOME = re.compile(r"(?:/Users/[^/\s]+|/home/[^/\s]+|[A-Za-z]:\\Users\\[^\\\s]+)")
MARKDOWN_LINK = re.compile(r"\[[^\]\n]+\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


class PublicWorkflowContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")

    def lookup_example(self):
        examples = re.findall(r"```bash\n(.*?)\n```", self.skill, re.S)
        examples = [example for example in examples if "NOT_CONFIGURED" in example]
        self.assertEqual(
            len(examples), 1,
            "Keep one runnable repository-state lookup example with NOT_CONFIGURED output.",
        )
        return examples[0]

    def run_lookup(self, directory, configured_path):
        state = directory / "state" / "dotfiles-sync" / "repo-path"
        state.parent.mkdir(parents=True)
        state.write_text(str(configured_path) + "\n", encoding="utf-8")
        before = state.read_bytes()
        # No inherited credentials, agent environment, or real-home state.
        result = subprocess.run(
            ["bash", "--noprofile", "--norc", "-c", self.lookup_example()],
            env={"PATH": os.defpath, "HOME": str(directory / "home"),
                 "XDG_STATE_HOME": str(directory / "state")},
            cwd=directory, capture_output=True, text=True, timeout=5,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(state.read_bytes(), before, "Lookup must not rewrite saved state.")
        self.assertFalse((configured_path / "private").exists(),
                         "Public-only lookup must not initialize private.")
        return result.stdout.strip()

    def test_lookup_accepts_directory_and_worktree_git_metadata(self):
        # Both layouts are supported; a path with spaces must remain quoted.
        for kind in ("directory", "file"):
            with self.subTest(metadata=kind), tempfile.TemporaryDirectory() as raw:
                directory = Path(raw)
                repo = directory / "public checkout"
                repo.mkdir()
                metadata = repo / ".git"
                if kind == "directory":
                    metadata.mkdir()
                else:
                    metadata.write_text("gitdir: fixture-metadata\n", encoding="utf-8")
                self.assertEqual(
                    self.run_lookup(directory, repo), f"REPO={repo}",
                    "The documented lookup rejects .git files used by linked worktrees/submodules.",
                )

    def test_lookup_rejects_path_without_git_metadata(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            repo = directory / "ordinary directory"
            repo.mkdir()
            self.assertEqual(self.run_lookup(directory, repo), "NOT_CONFIGURED")

    def test_private_extension_is_explicitly_optional_local_reference(self):
        links = MARKDOWN_LINK.findall(self.skill)
        self.assertTrue(
            any(target.split("#", 1)[0].endswith(OPTIONAL_EXTENSION) for target in links),
            "Link the optional private/docs/DOTFILES-SYNC.md extension; public must work without it.",
        )
        # Deliberately do not read or require the optional private target.

    def test_extension_lookup_uses_discovered_repo_when_skill_is_home_symlink(self):
        for present in (False, True):
            with self.subTest(extension_present=present), tempfile.TemporaryDirectory() as raw:
                directory = Path(raw)
                repo = directory / "public checkout"
                repo.mkdir()
                home = directory / "fake home"
                home.mkdir()
                skill_link = home / "dotfiles-sync"
                skill_link.symlink_to(SKILL_DIR, target_is_directory=True)
                loaded = (skill_link / "SKILL.md").read_text(encoding="utf-8")
                examples = [example for example in re.findall(r"```bash\n(.*?)\n```", loaded, re.S)
                            if "$REPO/private/docs/DOTFILES-SYNC.md" in example]
                self.assertEqual(
                    len(examples), 1,
                    "Document one optional extension lookup using $REPO/private/docs/DOTFILES-SYNC.md "
                    "after repository discovery; a Markdown-relative link breaks via home symlinks.",
                )
                extension = repo / OPTIONAL_EXTENSION
                if present:
                    extension.parent.mkdir(parents=True)
                    extension.write_text("Synthetic extension.\n", encoding="utf-8")
                result = subprocess.run(
                    ["bash", "--noprofile", "--norc", "-c", examples[0]],
                    env={"PATH": os.defpath, "HOME": str(home), "REPO": str(repo)},
                    cwd=home, capture_output=True, text=True, timeout=5,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(), str(extension) if present else "")
                self.assertEqual((repo / "private").exists(), present,
                                 "Missing optional private must not be created during lookup.")

    def test_local_reference_targets_work_without_private_checkout(self):
        for document in sorted(SKILL_DIR.rglob("*.md")):
            for target in MARKDOWN_LINK.findall(document.read_text(encoding="utf-8")):
                if re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:", target) or target.startswith("#"):
                    continue
                relative = target.split("#", 1)[0]
                resolved = (document.parent / relative).resolve()
                with self.subTest(document=document.relative_to(ROOT), target=target):
                    self.assertTrue(resolved.is_relative_to(ROOT),
                                    "Local references must stay inside the delivered checkout.")
                    if resolved == ROOT / OPTIONAL_EXTENSION:
                        continue
                    self.assertFalse(resolved.is_relative_to(ROOT / "private"),
                                     "Use the optional extension contract instead of private implementation links.")
                    self.assertTrue(resolved.exists(), "Broken local workflow reference.")

    def test_public_workflow_has_no_personal_inventory(self):
        # Personal source mappings and discovery belong to the private extension,
        # even when the implementation uses only generic language or stdlib.
        forbidden = {
            "personal agent home mapping": r"~/\.(?:hermes|grok)(?:/|\b)",
            "personal skill inventory": r"\{pkm\*[^}]*\}",
            "personal agent discovery": r"hermes\s+스킬\s+자동\s+발견",
        }
        for reason, pattern in forbidden.items():
            with self.subTest(boundary=reason):
                self.assertIsNone(re.search(pattern, self.skill, re.I),
                                  f"Move {reason} into the optional private extension.")

    def test_workflow_does_not_authorize_automatic_commits(self):
        forbidden = (
            r"commit\s*한다\s*\(자동\)",
            r"commit은\s*사용자에게\s*따로\s*묻지\s*않고\s*진행",
        )
        for pattern in forbidden:
            with self.subTest(rule=pattern):
                self.assertIsNone(re.search(pattern, self.skill, re.I),
                                  "Commit requires authorization from the current user request.")

    def test_workflow_has_no_machine_paths_or_scratch_dependencies(self):
        for document in sorted(SKILL_DIR.rglob("*.md")):
            text = document.read_text(encoding="utf-8")
            with self.subTest(document=document.relative_to(ROOT)):
                self.assertIsNone(MACHINE_HOME.search(text),
                                  "Use portable paths in the shared workflow.")
                self.assertNotRegex(text, r"(?:cache/scratch/|\.pipeline-test-tmp/)",
                                    "Disposable scratch output cannot be a reusable source dependency.")

    def test_ghostty_template_comments_have_no_machine_home(self):
        # UI defaults remain public; only generated template commentary is checked.
        for lineno, line in enumerate((ROOT / "ghostty/config").read_text().splitlines(), 1):
            if line.lstrip().startswith("#"):
                with self.subTest(line=lineno):
                    self.assertIsNone(MACHINE_HOME.search(line),
                                      "Replace the generated machine-home comment with portable prose.")


if __name__ == "__main__":
    unittest.main()
