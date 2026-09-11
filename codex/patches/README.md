# Codex plugin compatibility patches

## security-guidance 2.0.8

Codex 0.154.0 rejects the Claude-specific `metrics` and `rewakeSummary`
fields in hook output. This patch logs metrics and maps notification
summaries to `systemMessage`. Security findings, decisions, stderr, and
exit codes remain unchanged. Apply it only to the Codex plugin cache;
the Claude installation keeps its original output protocol.

From the dotfiles repository root, after installing this plugin version:

```sh
patch -d "$HOME/.codex/plugins/cache/claude-plugins-official/security-guidance/2.0.8" -p1 < codex/patches/security-guidance-2.0.8-codex-output.patch
```

Plugin updates can replace cached files. Check whether the new version
still needs this fix before adapting or reapplying the patch.
