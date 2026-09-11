# Codex plugin compatibility patches

## security-guidance 2.0.8

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
