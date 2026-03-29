# Codex Runner

`tools/codex-runner.sh` is a local command wrapper intended to reduce repeated permission prompts while keeping a few reasonable guardrails in place.

What it does:

- restricts `--cwd` to this worktree and the original MoneyPrinterV2 repo
- allows a practical set of development commands
- blocks obviously risky heads like `sudo`, `ssh`, `scp`, `rsync`, `rm`, and `dd`
- blocks inline `bash -c`, `python -c`, and `node -e` execution
- restricts `curl` to localhost URLs
- logs executions to `.codex-runner.log`

Usage:

```bash
tools/codex-runner.sh --cwd /private/tmp/MoneyPrinterV2-citevideo -- git status --short
tools/codex-runner.sh --cwd /private/tmp/MoneyPrinterV2-citevideo --env CITEVIDEO_ROUNDTABLE_ROUNDS=2 -- python3 -m unittest tests.test_topic_package
```

This runner is intentionally local and pragmatic. If a task genuinely needs something outside these guardrails, we can still use a normal one-off approval for that command.
