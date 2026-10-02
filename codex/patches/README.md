# Codex plugin compatibility patches

## Preferred setup

Use the official Codex distributions rather than repeatedly patching a
Claude plugin cache. Cache refreshes replaced the security-guidance patch
and brought its hook failures back.

```sh
codex plugin add superpowers@openai-curated-remote
codex plugin add codex-security@openai-curated-remote
```

Merge the selective preferences from `../plugins.toml` into the local
`~/.codex/config.toml`. Do not replace the entire local config, symlink it,
or copy authentication, hook trust, or session state into this repository.
Leave other plugins and the global hooks setting unchanged.

| Capability | Codex setup |
| --- | --- |
| Development workflow | `superpowers@openai-curated-remote` (6.4.2 verified) |
| Security review | `codex-security@openai-curated-remote` (0.1.31 verified) |
| Skill authoring | Built-in Codex `skill-creator` skill |
| Persistent iteration | Native Codex goals; start only when explicitly requested |

The Claude versions remain installed but disabled in Codex. The separate
Claude installation is unaffected. Codex Security provides security review
workflows; it does not reproduce the Claude plugin's automatic background
reviews or require its Anthropic API credentials.

The original security-guidance failures have two causes: Claude-only
`metrics`/`rewakeSummary` JSON fields, and a push handler calling `.get()` on
Codex's string `tool_response`. Its seven Bash handlers also rely on Claude's
`if` filtering. The already-loaded handlers in a running turn may need the
legacy output patch and a string-to-object normalization while that turn
finishes; freshly started Codex sessions use the disabled plugin preference.
Do not rely on cache patches as the permanent configuration.

## security-guidance 2.0.8

Legacy reference for sessions still using the Claude plugin.

Codex 0.154.0 rejects the Claude-specific `metrics` and `rewakeSummary`
fields in hook output. This patch logs metrics and maps notification
summaries to `systemMessage`. Security findings, decisions, stderr, and
exit codes remain unchanged. The SessionStart SDK bootstrap also emits a
Claude async preamble followed by a metrics object, which Codex cannot parse
as one JSON response. The patch removes that preamble and logs the bootstrap
metrics, while preserving SDK setup and user notices. The bootstrap runs
synchronously within its existing 180-second timeout.

Apply it only to the Codex plugin cache;
the Claude installation keeps its original output protocol.

From the dotfiles repository root, after installing this plugin version:

```sh
patch -d "$HOME/.codex/plugins/cache/claude-plugins-official/security-guidance/2.0.8" -p1 < codex/patches/security-guidance-2.0.8-codex-output.patch
```

Plugin updates or cache refreshes can replace patched files even when the
version stays the same. Check whether the installed files still need this
fix before adapting or reapplying the patch. If the earlier patch is already
applied, use `patch --forward` to skip its existing hunks and apply the new
SessionStart hunks; inspect the output for any other rejected hunks.
