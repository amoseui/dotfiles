"""Exercise the prompt with real Git repos; all state stays in this worktree."""
from pathlib import Path
import os
import pty
import re
import select
import signal
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "zsh/git-prompt.zsh"
GIT = shutil.which("git") or "git"


class GitPromptTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix=".prompt-test-", dir=ROOT)
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base / "repo"
        self.repo.mkdir()
        self.env = {
            "PATH": os.pathsep.join([str(Path(GIT).parent), "/usr/bin", "/bin"]),
            "HOME": str(self.base), "TMPDIR": str(self.base),
            "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null",
            "LC_ALL": "C", "TERM": "xterm-256color", "PYTHONDONTWRITEBYTECODE": "1",
            "HELPER": str(HELPER), "REPO": str(self.repo), "BASE": str(self.base),
            "GIT_CEILING_DIRECTORIES": str(self.base),
        }
        self.git("init", "-q", "-b", "main")
        (self.repo / "tracked").write_text("original\n")
        self.git("add", "tracked")
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.com",
                 "commit", "-qm", "fixture")

    def git(self, *args, repo=None):
        return subprocess.run([GIT, "-C", str(repo or self.repo), *args],
                              env=self.env, check=True, capture_output=True, text=True).stdout

    def run_zsh(self, body, before_source=""):
        setup = '''
            autoload -Uz add-zsh-hook
            ZSH_THEME_GIT_PROMPT_PREFIX='git:'
            ZSH_THEME_GIT_PROMPT_SUFFIX=''
            ZSH_THEME_GIT_PROMPT_CLEAN=' o'
            ZSH_THEME_GIT_PROMPT_DIRTY=' x'
            source "$HELPER"
            cd "$REPO"
            zmodload zsh/zselect
            zmodload zsh/datetime
            pump() {
                local -F deadline=$(( EPOCHREALTIME + $1 ))
                while (( EPOCHREALTIME < deadline )); do
                    if (( _dotfiles_git_fd >= 0 )); then
                        zselect -t 1 -r $_dotfiles_git_fd &&
                            _dotfiles_git_callback $_dotfiles_git_fd
                    else
                        zselect -t 1
                    fi
                done
                return 0
            }
            started() {
                repeat 200 { [[ -s $CALLS ]] && return 0; zselect -t 1; }
                print -u2 -- 'worker never started'
                return 1
            }
            settle() {
                repeat 300 {
                    (( _dotfiles_git_fd < 0 )) && return 0
                    zselect -t 2 -r $_dotfiles_git_fd &&
                        _dotfiles_git_callback $_dotfiles_git_fd
                }
                print -u2 -- 'worker timeout'
                return 1
            }
        '''
        setup = setup.replace('source "$HELPER"', before_source + '\nsource "$HELPER"')
        result = subprocess.run(["/bin/zsh", "-dfc", setup + body], env=self.env,
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        return result.stdout.splitlines()

    def controlled_git(self, delay: float = 0, error: int = 0):
        """Delay a real status snapshot to expose races, never replace its data."""
        bindir = self.base / "bin"
        bindir.mkdir()
        self.control = self.base / "control"
        self.log = self.base / "calls"
        self.control.write_text(f"{delay} {error}")
        wrapper = bindir / "git"
        wrapper.write_text(f'''#!{sys.executable}
import os, subprocess, sys, time
from pathlib import Path
args = sys.argv[1:]
if args[:1] == ['-C']:
    args = args[2:]
if args[:1] != ['status']:
    os.execv({GIT!r}, [{GIT!r}] + sys.argv[1:])
delay, error = Path(os.environ['CONTROL']).read_text().split()
result = subprocess.run([{GIT!r}] + sys.argv[1:], capture_output=True)
child = None
if os.environ.get('SPAWN_CHILD'):
    child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])
with open(os.environ['CALLS'], 'a') as log:
    log.write(f'start {{os.getpid()}} {{os.getpgrp()}} {{child.pid if child else 0}}\\n')
if float(delay) < 0:
    while not Path(os.environ['BASE'], 'release').exists():
        time.sleep(0.01)
else:
    time.sleep(float(delay))
with open(os.environ['CALLS'], 'a') as log:
    log.write('finish\\n')
sys.stdout.buffer.write(result.stdout)
sys.exit(int(error) or result.returncode)
''')
        wrapper.chmod(0o755)
        self.env.update(PATH=str(bindir) + os.pathsep + self.env["PATH"],
                        CONTROL=str(self.control), CALLS=str(self.log))

    def test_branch_is_immediate_and_pending_is_unknown(self):
        # A missing/synchronous prompt must not publish a clean result yet.
        self.assertEqual(self.run_zsh('''
            _dotfiles_git_precmd
            print -r -- "$(git_prompt_info)"
            _dotfiles_git_cleanup
        '''), ["git:main ?"])

    def test_repeated_enter_does_not_restart_running_scan(self):
        self.controlled_git(delay=-1)
        self.assertEqual(self.run_zsh('''
            _dotfiles_git_precmd; started
            repeat 5 { _dotfiles_git_precmd; pump 0.02; }
            print release > "$BASE/release"
            settle
            print -r -- "$(git_prompt_info)"
            _dotfiles_git_cleanup
        '''), ["git:main o"])
        self.assertEqual([line.split()[0] for line in self.log.read_text().splitlines()],
                         ["start", "finish"])

    def test_commands_during_scan_coalesce_one_fresh_followup(self):
        self.controlled_git(delay=0.2)
        self.assertEqual(self.run_zsh('''
            _dotfiles_git_precmd; started
            repeat 3 {
                _dotfiles_git_preexec
                print changed >> tracked
                _dotfiles_git_precmd
            }
            print -r -- "$(git_prompt_info)"
            settle
            print -r -- "$(git_prompt_info)"
            _dotfiles_git_cleanup
        '''), ["git:main ?", "git:main x"])
        self.assertEqual([line.split()[0] for line in self.log.read_text().splitlines()],
                         ["start", "finish", "start", "finish"])

    def test_result_while_command_runs_waits_for_next_precmd(self):
        self.controlled_git(delay=0.1)
        self.assertEqual(self.run_zsh('''
            _dotfiles_git_precmd; started
            _dotfiles_git_preexec
            print changed >> tracked
            pump 0.3
            print -r -- "$(git_prompt_info)"
            print -r -- "$(grep -c start "$CALLS")"
            _dotfiles_git_precmd; settle
            print -r -- "$(git_prompt_info)"
            _dotfiles_git_cleanup
        '''), ["git:main ?", "1", "git:main x"])

    def test_branch_and_detached_head_change_immediately(self):
        self.controlled_git(delay=0.2)
        sha = self.git("rev-parse", "HEAD").strip()[:10]
        self.assertEqual(self.run_zsh('''
            _dotfiles_git_precmd; settle
            command git switch -qc next
            _dotfiles_git_precmd
            print -r -- "$(git_prompt_info)"
            settle
            command git switch -q --detach
            _dotfiles_git_precmd
            print -r -- "$(git_prompt_info)"
            settle
            print -r -- "$(git_prompt_info)"
            _dotfiles_git_cleanup
        '''), ["git:next ?", f"git:{sha} ?", f"git:{sha} o"])

    def test_nested_repo_and_nonrepo_never_show_old_result(self):
        nested = self.repo / "nested"
        nested.mkdir()
        self.git("init", "-q", "-b", "inner", repo=nested)
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.com",
                 "commit", "--allow-empty", "-qm", "fixture", repo=nested)
        (self.base / "plain").mkdir()
        self.controlled_git(delay=0.2)
        self.assertEqual(self.run_zsh('''
            _dotfiles_git_precmd; started
            cd nested
            _dotfiles_git_precmd
            print -r -- "$(git_prompt_info)"
            settle
            print -r -- "$(git_prompt_info)"
            cd "$BASE/plain"
            print -r -- "outside:$(git_prompt_info)"
            _dotfiles_git_precmd
            print -r -- "outside:$(git_prompt_info)"
            pump 0.25
            print -r -- "outside:$(git_prompt_info)"
            _dotfiles_git_cleanup
        '''), ["git:inner ?", "git:inner o", "outside:", "outside:", "outside:"])

    def test_linked_worktrees_have_separate_repo_identity(self):
        linked = self.base / "linked"
        self.git("worktree", "add", "-q", "--detach", str(linked))
        self.assertEqual(self.run_zsh('''
            _dotfiles_git_precmd; settle
            first=$_dotfiles_git_repo
            cd "$BASE/linked"
            _dotfiles_git_precmd
            [[ $first != $_dotfiles_git_repo ]] && print separate
            [[ $_dotfiles_git_repo == /* ]] && print absolute
            _dotfiles_git_cleanup
        '''), ["separate", "absolute"])

    def test_cleanup_kills_worker_git_and_its_child_and_closes_fd(self):
        self.controlled_git(delay=-1)
        self.env["SPAWN_CHILD"] = "1"
        self.assertEqual(self.run_zsh('''
            _dotfiles_git_precmd; started
            fd=$_dotfiles_git_fd
            _dotfiles_git_cleanup
            if { true <&$fd } 2>/dev/null; then print leaked; else print closed; fi
            zpty -L
        '''), ["closed"])
        _, pid, group, child = self.log.read_text().split()
        self.assertNotEqual(int(group), os.getpgrp())
        for target in (int(pid), int(child)):
            self.assert_process_gone(target)

    def assert_process_gone(self, pid):
        for _ in range(100):
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                return
            time.sleep(0.01)
        # Do not leave a regressed fixture process running after the assertion.
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        self.fail(f"fixture process {pid} survived cleanup")

    def test_source_twice_cancels_old_job_and_keeps_one_hook_each(self):
        self.controlled_git(delay=-1)
        self.assertEqual(self.run_zsh('''
            _dotfiles_git_precmd; started
            source "$HELPER"
            source "$HELPER"
            print -r -- $precmd_functions[(R)_dotfiles_git_precmd] \
                $preexec_functions[(R)_dotfiles_git_preexec] \
                $chpwd_functions[(R)_dotfiles_git_chpwd] \
                $zshexit_functions[(R)_dotfiles_git_cleanup]
            zpty -L
            print release > "$BASE/release"
            _dotfiles_git_precmd; settle
            print -r -- "$(git_prompt_info)"
            _dotfiles_git_cleanup
        '''), ["_dotfiles_git_precmd _dotfiles_git_preexec _dotfiles_git_chpwd "
               "_dotfiles_git_cleanup", "git:main o"])
        self.assertEqual([line.split()[0] for line in self.log.read_text().splitlines()],
                         ["start", "start", "finish"])

    def test_omz_deferred_registration_preserves_other_handlers(self):
        before = '''
            other_handler() { print other; }
            _omz_git_prompt_status() { print status; }
            _omz_git_prompt_info() { print stale; }
            _omz_async_functions=(other_handler)
            typeset -A _OMZ_ASYNC_OUTPUT
            _OMZ_ASYNC_OUTPUT[other_handler]=keep
            _OMZ_ASYNC_OUTPUT[_omz_git_prompt_info]=stale
            _defer_async_git_register() {
                _omz_async_functions+=(_omz_git_prompt_info _omz_git_prompt_status)
                add-zsh-hook -d precmd _defer_async_git_register
                unfunction _defer_async_git_register
            }
            add-zsh-hook precmd _defer_async_git_register
        '''
        self.assertEqual(self.run_zsh('''
            source "$HELPER"
            for hook in $precmd_functions; do $hook; done
            print -r -- "${(j: :)_omz_async_functions}"
            print -r -- "${_OMZ_ASYNC_OUTPUT[other_handler]}"
            print -r -- "old:${_OMZ_ASYNC_OUTPUT[_omz_git_prompt_info]}"
            _dotfiles_git_cleanup
        ''', before), ["other_handler _omz_git_prompt_status", "keep", "old:"])

    def test_rc_sources_helper_relative_to_symlink_target(self):
        # Run only the final, dependency-free rc section, never the real rc.
        tail = (ROOT / "zsh/zshrc").read_text().split(
            "# Resolve this file's symlink", 1)[1]
        directory = self.base / "rc"
        directory.mkdir()
        (directory / "zshrc").write_text("# Resolve this file's symlink" + tail)
        for name in ("git-prompt.zsh", "handoff-prompt.zsh"):
            shutil.copyfile(ROOT / "zsh" / name, directory / name)
        (self.base / "rc-link").symlink_to(directory / "zshrc")
        self.assertEqual(self.run_zsh('''
            unfunction _dotfiles_git_precmd git_prompt_info
            source "$BASE/rc-link"
            _dotfiles_git_precmd; settle
            print -r -- "$(git_prompt_info)"
            _dotfiles_git_cleanup
        '''), ["git:main o"])

    def start_interactive(self):
        pid, fd = pty.fork()
        if pid == 0:
            os.chdir(self.repo)
            os.execve("/bin/zsh", ["zsh", "-d", "-f", "-i"], self.env)
        self.addCleanup(self.close_interactive, pid, fd)
        self.pty_fd = fd
        self.pty_output = ""
        self.read_until("% ")
        self.pty_send('unset HISTFILE; setopt promptsubst; '
                      "ZSH_THEME_GIT_PROMPT_PREFIX='git:'; ZSH_THEME_GIT_PROMPT_SUFFIX=''; "
                      "ZSH_THEME_GIT_PROMPT_CLEAN=' o'; ZSH_THEME_GIT_PROMPT_DIRTY=' x'; "
                      "PS1='READY[$(git_prompt_info)]> '; source \"$HELPER\"\n")
        return pid

    def close_interactive(self, pid, fd):
        try:
            os.write(fd, b"exit\n")
            for _ in range(100):
                if os.waitpid(pid, os.WNOHANG)[0]:
                    break
                time.sleep(0.01)
            else:
                os.kill(pid, signal.SIGKILL)
                os.waitpid(pid, 0)
        except (OSError, ChildProcessError):
            pass
        finally:
            os.close(fd)

    def pty_send(self, text):
        self.pty_output = ""
        os.write(self.pty_fd, text.encode())

    def read_until(self, wanted, timeout=5):
        deadline = time.monotonic() + timeout
        while wanted not in self.pty_output and time.monotonic() < deadline:
            readable, _, _ = select.select([self.pty_fd], [], [], 0.05)
            if readable:
                try:
                    data = os.read(self.pty_fd, 65536)
                except OSError:
                    break
                if not data:
                    break
                self.pty_output += re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "",
                                          data.decode(errors="replace"))
        self.assertIn(wanted, self.pty_output)

    def test_interactive_zle_redraw_and_enter_do_not_starve(self):
        self.controlled_git(delay=-1)
        self.start_interactive()
        self.read_until("READY[git:main ?]>")
        for _ in range(5):
            self.pty_send("\n")
            self.read_until("READY[git:main ?]>")
        (self.base / "release").write_text("go")
        self.read_until("READY[git:main o]>")
        self.assertEqual([line.split()[0] for line in self.log.read_text().splitlines()],
                         ["start", "finish"])
        self.pty_send("print changed >> tracked\n")
        self.read_until("READY[git:main x]>")
        self.pty_send("git switch -qc next\n")
        self.read_until("READY[git:next x]>")
        self.assertNotIn("error", self.pty_output.lower())

    def test_interactive_exit_cleans_external_child(self):
        self.controlled_git(delay=-1)
        self.env["SPAWN_CHILD"] = "1"
        shell = self.start_interactive()
        self.read_until("READY[git:main ?]>")
        for _ in range(200):
            if self.log.exists() and self.log.read_text().strip():
                break
            time.sleep(0.01)
        self.assertTrue(self.log.exists())
        _, pid, group, child = self.log.read_text().split()
        self.pty_send("exit\n")
        exited = False
        for _ in range(200):
            if os.waitpid(shell, os.WNOHANG)[0]:
                exited = True
                break
            readable, _, _ = select.select([self.pty_fd], [], [], 0.01)
            if readable:
                try:
                    self.pty_output += os.read(self.pty_fd, 65536).decode(errors="replace")
                except OSError:
                    break
        self.assertTrue(exited, self.pty_output)
        self.assert_process_gone(int(pid))
        self.assert_process_gone(int(child))

    def test_clean_tracked_and_untracked_results(self):
        self.assertEqual(self.run_zsh('''
            _dotfiles_git_precmd; settle
            print -r -- "$(git_prompt_info)"
            print changed >> tracked
            _dotfiles_git_precmd; settle
            print -r -- "$(git_prompt_info)"
            command git restore tracked
            print new > untracked
            _dotfiles_git_precmd; settle
            print -r -- "$(git_prompt_info)"
            _dotfiles_git_cleanup
        '''), ["git:main o", "git:main x", "git:main x"])

    def test_failed_status_is_unknown_even_with_empty_output(self):
        self.controlled_git(error=128)
        self.assertEqual(self.run_zsh('''
            _dotfiles_git_precmd; settle
            print -r -- "$(git_prompt_info)"
            _dotfiles_git_cleanup
        '''), ["git:main ?"])

    def test_unexpected_worker_death_is_unknown_and_fd_is_closed(self):
        self.controlled_git(delay=-1)
        self.assertEqual(self.run_zsh('''
            _dotfiles_git_precmd; started
            read -r tag pid group child < "$CALLS"
            kill -KILL -- -$group
            settle
            print -r -- "$(git_prompt_info)"
            print -r -- $_dotfiles_git_fd
            _dotfiles_git_cleanup
        '''), ["git:main ?", "-1"])

    def test_changed_head_rejects_late_result_before_next_prompt(self):
        self.controlled_git(delay=-1)
        self.assertEqual(self.run_zsh('''
            _dotfiles_git_precmd; started
            command git switch -qc next
            print release > "$BASE/release"
            settle
            print -r -- "$(git_prompt_info)"
            _dotfiles_git_precmd; settle
            print -r -- "$(git_prompt_info)"
            _dotfiles_git_cleanup
        '''), ["git:next ?", "git:next o"])


if __name__ == "__main__":
    unittest.main()
