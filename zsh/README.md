# Git prompt

`git-prompt.zsh` keeps the theme's Git prefix, suffix, clean `o` and dirty
`x`. HEAD is read synchronously; the working-tree scan runs separately.
`?` means pending, unavailable, or failed, never a clean result.

The active context is an absolute git-dir plus worktree root, full HEAD
and branch name. Changing context invalidates old results. One worker runs
at a time; commands issued during a scan request one coalesced followup.
Empty Enter does not cancel or reschedule an in-flight scan. Results from
before the latest command cannot publish a clean or dirty state.

The final rc section resolves its symlink before sourcing the helper,
after Antigen and the theme. Only OMZ's replaced Git info handler is
detached; other async handlers remain registered.

The worker uses Zsh's `zsh/zpty` and `zsh/system` modules. Its own process
group includes Git's children. Context changes, re-sourcing and shell exit
close the PTY and terminate that group. No Git configuration or persistent
cache is written; status runs with `GIT_OPTIONAL_LOCKS=0`.

Tests use Zsh and Python's standard library, create isolated Git fixtures
under the checkout, and do not load user startup files or installed OMZ.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s scripts -v
zsh -n zsh/git-prompt.zsh zsh/zshrc
```
