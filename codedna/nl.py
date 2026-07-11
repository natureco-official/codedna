"""codedna/nl.py — Natural language router for CodeDNA, powered by Needle.

Lets a user type a request in plain language and have it translated
into the matching `codedna` CLI invocation. The model itself is
multilingual at the input level, so the command works regardless of
which language the user types in — only the code, comments, and
output messages are kept in English for consistency with the rest
of the project.

Usage (standalone):
    python -m codedna.nl "show me the AI score for my last commit"

Usage (from cli.py):
    from codedna.nl import route_command
    route_command(user_query)
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from needle import SimpleAttentionNetwork, load_checkpoint, generate, get_tokenizer

# ---------------------------------------------------------------------------
# Tool definitions — mirrors codedna_tools.json. Keep these two in sync.
# ---------------------------------------------------------------------------

TOOLS_PATH = Path(__file__).parent / "nl_tools.json"


def _load_tools() -> str:
    if TOOLS_PATH.exists():
        return TOOLS_PATH.read_text(encoding="utf-8")
    raise FileNotFoundError(
        f"{TOOLS_PATH} not found. Copy codedna_tools.json into codedna/ as nl_tools.json."
    )


# ---------------------------------------------------------------------------
# Needle model (loaded once, lazily)
# ---------------------------------------------------------------------------

# Checkpoint paths. The fine-tuned checkpoint (if present) takes priority
# over the base Hugging Face download. Both are kept under ~/.codedna/needle/
# so they are shared across projects and never committed by accident.
_CHECKPOINT_DIR = Path.home() / ".codedna" / "needle"
_FINETUNED_PATH = _CHECKPOINT_DIR / "needle-finetuned.pkl"
_CHECKPOINT_PATH = _CHECKPOINT_DIR / "needle.pkl"
_HF_REPO_ID = "Cactus-Compute/needle"
_HF_FILENAME = "needle.pkl"

_MODEL = None
_PARAMS = None
_TOKENIZER = None


def _resolve_checkpoint() -> Path:
    """Return the best available checkpoint path.

    Priority:
      1. Fine-tuned checkpoint at ~/.codedna/needle/needle-finetuned.pkl
      2. Already-downloaded base model at ~/.codedna/needle/needle.pkl
      3. Auto-downloaded from Hugging Face, cached at (2)
    """
    if _FINETUNED_PATH.exists():
        return _FINETUNED_PATH
    if _CHECKPOINT_PATH.exists():
        return _CHECKPOINT_PATH

    try:
        from huggingface_hub import hf_hub_download
    except ImportError as exc:
        raise ImportError(
            "huggingface_hub is required to auto-download the Needle checkpoint. "
            "Install it with: pip install codedna[nl]"
        ) from exc

    print("First run: downloading the Needle model (~53 MB)...", file=sys.stderr)
    _CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    downloaded_path = hf_hub_download(repo_id=_HF_REPO_ID, filename=_HF_FILENAME)

    # hf_hub_download caches under ~/.cache/huggingface; copy it into our own
    # checkpoint dir so the path stays stable and predictable for the CLI.
    import shutil
    shutil.copyfile(downloaded_path, _CHECKPOINT_PATH)
    print(f"Needle model cached at {_CHECKPOINT_PATH}", file=sys.stderr)
    return _CHECKPOINT_PATH


def _ensure_model_loaded() -> None:
    global _MODEL, _PARAMS, _TOKENIZER
    if _MODEL is not None:
        return
    checkpoint_path = _resolve_checkpoint()
    params, config = load_checkpoint(str(checkpoint_path))
    _MODEL = SimpleAttentionNetwork(config)
    _PARAMS = params
    _TOKENIZER = get_tokenizer()


# ---------------------------------------------------------------------------
# Mapping from tool call -> actual `codedna` CLI argv
# ---------------------------------------------------------------------------

def _build_argv(name: str, args: dict) -> list[str]:
    """Translate a Needle tool call into a `codedna ...` argv list."""

    def opt(flag: str, key: str, cast=str) -> list[str]:
        if key in args and args[key] not in (None, ""):
            return [flag, str(cast(args[key]))]
        return []

    def flag(name_flag: str, key: str) -> list[str]:
        return [name_flag] if args.get(key) else []

    mapping = {
        "scan": ["scan", *opt("--max", "max_files", int), *opt("--min-risk", "min_risk", float)],
        "status": ["status"],
        "commit_history": ["history", *opt("--limit", "limit", int)],
        "bus_factor": [
            "bus-factor",
            *flag("--critical", "critical"),
            *opt("--max", "max_files", int),
        ],
        "debt": ["debt", *opt("--rate", "rate", float), *opt("--file", "file")],
        "protect_add": [
            "protect", "add", str(args.get("file_path", "")),
            *opt("--threshold", "threshold", float),
            *opt("--label", "label"),
        ],
        "protect_remove": ["protect", "remove", str(args.get("file_path", ""))],
        "protect_list": ["protect", "list"],
        "protect_check": ["protect", "check"],
        "sprint_create": [
            "sprint", "create",
            "--name", str(args.get("name", "")),
            "--start", str(args.get("start", "")),
            "--end", str(args.get("end", "")),
        ],
        "sprint_health": ["sprint", "health"],
        "sprint_history": ["sprint", "history", *opt("--limit", "limit", int)],
        "export": ["export", *opt("--format", "fmt"), *opt("--output", "output")],
        "webhook_show": ["webhook", "--show"],
        "webhook_test": ["webhook", "--test"],
        "webhook_reset": ["webhook", "--reset"],
        "watch": [
            "watch",
            *opt("--interval", "interval", int),
            *flag("--once", "once"),
            *flag("--notify", "notify"),
        ],
        "report": ["report"],
        "doctor": ["doctor"],
    }

    if name not in mapping:
        raise ValueError(f"Unknown tool name returned by Needle: {name!r}")
    return mapping[name]


# Commands that change state. At the current model accuracy, a misrouted
# request here (e.g. "protect" resolving to protect_remove instead of
# protect_add) can do the opposite of what the user asked. These always
# require an explicit confirmation, regardless of --dry-run.
_MUTATING_TOOLS = {
    "protect_add",
    "protect_remove",
    "sprint_create",
    "webhook_reset",
}


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------

def route_command(user_query: str, dry_run: bool = False) -> None:
    """Parse `user_query` with Needle and run the matching codedna command(s)."""
    _ensure_model_loaded()

    raw = generate(
        _MODEL, _PARAMS, _TOKENIZER,
        query=user_query,
        tools=_load_tools(),
        stream=False,
    )

    try:
        calls = json.loads(raw)
    except json.JSONDecodeError:
        print(f"Unexpected output from Needle: {raw}", file=sys.stderr)
        return

    if not calls:
        print("Could not match that request to a known command. Try rephrasing.")
        return

    for call in calls:
        name = call.get("name")
        args = call.get("arguments", {})
        try:
            argv = _build_argv(name, args)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            continue

        full_cmd = ["codedna", *argv]
        print(f"-> {' '.join(full_cmd)}")

        if dry_run:
            continue

        if name in _MUTATING_TOOLS:
            # Needle is a small (26M parameter) model and can misroute
            # requests, especially the difference between "protect" and
            # "unprotect" intents. Never run a state-changing command
            # silently — always get an explicit yes from the user first.
            answer = input("Run this command? [y/N] ").strip().lower()
            if answer not in ("y", "yes"):
                print("Skipped.")
                continue

        subprocess.run(full_cmd)


if __name__ == "__main__":
    query = " ".join(sys.argv[1:])
    if not query:
        print("Usage: python -m codedna.nl '<your request in natural language>'")
        sys.exit(1)
    route_command(query)
