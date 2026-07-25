# Integrating Needle into CodeDNA

## 1. Place the files

```
codedna/
├── cli.py
├── nl.py                  ← copy this file here
├── nl_tools.json           ← copy codedna_tools.json here, renamed
└── ...
```

```bash
cp codedna_tools.json codedna/nl_tools.json
cp nl.py codedna/nl.py
```

## 2. Add needle as an optional dependency

Needle pulls in JAX, which is a heavy dependency most CodeDNA users (who only
run `scan`, `status`, `debt`, etc.) don't need. So instead of adding it to the
base `dependencies` list, add it as an extra in `pyproject.toml`:

```toml
[project.optional-dependencies]
nl = [
    "needle @ git+https://github.com/cactus-compute/needle.git",
    "huggingface_hub",
]
```

Users who want the `ask` command install it with:

```bash
pip install "codedna[nl]"
```

This is the one place a manual step is unavoidable — Needle isn't published
on PyPI itself, only as a GitHub source, so it can't simply ride along as a
plain dependency the way the rest of CodeDNA's requirements do.

### Model weights download automatically — no separate setup step

`nl.py` checks for the checkpoint on first use and pulls it from Hugging Face
(`Cactus-Compute/needle`) automatically if missing, caching it under
`~/.codedna/needle/needle.pkl`. There is no need to clone the Needle repo or
run `needle playground` manually — the first `codedna ask ...` call handles
it:

```
$ codedna ask "show me the bus factor for critical files only"
First run: downloading the Needle model (~53 MB)...
Needle model cached at /home/you/.codedna/needle/needle.pkl
-> codedna bus-factor --critical
```

The ~53 MB checkpoint is intentionally *not* bundled inside the `codedna`
package itself — that would bloat every install by orders of magnitude for
users who never touch `ask`, and would tie your release cadence to Needle's.
Downloading once on first use, then caching, gives the same "it just works"
experience without that cost.

## 3. Add the new command to cli.py

Add this next to the other `@app.command()` definitions (e.g. right after the
`doctor` command):

```python
@app.command()
def ask(
    query: list[str] = typer.Argument(..., help="What you want to do, in plain language."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show the command without running it."),
) -> None:
    """Run a CodeDNA command from a natural-language request (powered by Needle)."""
    from codedna.nl import route_command
    route_command(" ".join(query), dry_run=dry_run)
```

## 4. Try it

```bash
codedna ask "show me the AI score for my last commit"
codedna ask "protect the auth folder from AI changes"
codedna ask "show me the bus factor for critical files only"
codedna ask "create Sprint 14 from July 1st to July 14th" --dry-run
```

### A note on accuracy

In testing against this 18-tool set, the unmodified Needle checkpoint
resolved about half of plain-English requests correctly, and essentially none
of the Turkish ones — the 26M-parameter model wasn't trained on this specific
tool set, and its multilingual function-calling is weak out of the box. Two
mitigations are in place because of this:

1. Tool names and descriptions in `nl_tools.json` were rewritten to reduce
   confusion between similarly-named commands (e.g. `doctor` vs
   `sprint_health`, `commit_history` vs `sprint_history`).
2. `nl.py` requires an explicit `y/N` confirmation before running any
   state-changing command (`protect_add`, `protect_remove`, `sprint_create`,
   `webhook_reset`), even without `--dry-run`. Read-only commands (`scan`,
   `status`, `commit_history`, `debt`, etc.) still run immediately.

For production-grade accuracy — including reliable Turkish support — fine-tune
the checkpoint on this exact tool set. See `finetune_data.jsonl` and the
"Fine-tuning" section below.

## Fine-tuning for better accuracy

The disambiguation fixes above help, but the real fix for low accuracy
(especially on Turkish queries and the `protect_add`/`protect_remove`
distinction) is fine-tuning Needle on this exact tool set.

1. Take `finetune_data.jsonl` (provided alongside this guide) as a starting
   point — it covers every tool with both English and Turkish phrasings,
   including the ambiguous pairs that failed in testing.
2. Add more examples from your own real usage, especially ones that fail in
   `--dry-run` testing.
3. Run:
   ```bash
   needle finetune finetune_data.jsonl
   ```
   or use the Playground's "Finetune on these tools" button with
   `nl_tools.json` loaded, which can also generate additional synthetic
   training data via Gemini.
4. Point `_CHECKPOINT_PATH` in `nl.py` at the resulting fine-tuned checkpoint
   instead of the auto-downloaded base one.
5. Re-run the same dry-run test matrix used during evaluation and confirm
   accuracy improved before removing the confirmation gate on mutating
   commands.

## Notes

- The `_build_argv` function in `nl.py` translates Needle's tool names into
  real `codedna` CLI arguments. If you add a new command to `cli.py`, update
  both `nl_tools.json` and this function — they need to stay in sync.
- Since the model runs on CPU, each call takes milliseconds; you won't notice
  added latency.
- Plan-gated commands (`bus-factor`, `sprint *`, etc., which require a Team
  plan) are already checked inside `codedna` itself via `is_feature_available`.
  Needle only picks the right command — it doesn't handle authorization.
- This tool set has no free-text fields (only paths, numbers, and dates), so
  the risk of the model echoing the raw query instead of structuring it — which
  we saw with an open-ended email body in testing — is low here.
- Needle requires Python 3.11+, while CodeDNA's base package supports 3.10+.
  Document this in your `[nl]` extra so users on 3.10 get a clear error
  instead of a confusing install failure.
