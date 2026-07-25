"""Commit understanding survey module."""

from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import IntPrompt
from rich.text import Text

console = Console()


def _get_score(question: str, question_no: int) -> Optional[int]:
    """
    Get a valid score between 1 and 5.

    Return values:
      - int (1-5) : user entered a score
      - None      : user intentionally skipped (0 or Enter),
                    or stdin could not be read (EOFError — environment issue)

    EOFError and KeyboardInterrupt are caught separately:
      - KeyboardInterrupt → silently return None (user pressed Ctrl+C)
      - EOFError          → print warning + return None (stdin not connected)
    """
    try:
        value = IntPrompt.ask(
            f"  [bold cyan]{question_no}.[/bold cyan] {question} [dim]\\[1-5][/dim]",
            default=0,
        )
        if value == 0:
            return None
        return max(1, min(5, value))
    except KeyboardInterrupt:
        # User intentionally cancelled — silent
        return None
    except EOFError:
        # stdin could not be read — not an intentional user choice.
        # Show an informative warning instead of silently swallowing.
        #
        # Deliberately ASCII: this branch fires exactly when there is no terminal, which
        # is also when the output stream is most likely a legacy Windows code page. A "⚠"
        # here raised UnicodeEncodeError and turned a skipped survey into a traceback.
        console.print(
            "  [dim red]! Could not read terminal input for survey "
            "(stdin not connected). Skipping survey.[/dim red]"
        )
        return None


def run_survey(commit_hash: str) -> Optional[float]:
    """
    Run a 3-question understanding survey after a post-commit hook.

    Args:
        commit_hash: The commit hash this survey is linked to

    Returns:
        Average understanding score (1.0-5.0), or None if user skipped
    """
    console.print()
    console.print(
        Panel(
            Text.from_markup(
                f"[bold yellow]CodeDNA[/bold yellow] — Quick understanding survey for commit [dim]{commit_hash[:8]}[/dim]\n"
                "[dim]Press Enter to skip (0 = skip)[/dim]"
            ),
            border_style="yellow",
            padding=(0, 2),
        )
    )

    questions = [
        "Could you explain this change 3 months from now?",
        "Could you debug it if a bug appeared?",
        "Could you explain how it works to someone else?",
    ]

    scores: list[int] = []
    for i, question in enumerate(questions, start=1):
        score = _get_score(question, i)
        if score is None:
            # Intentionally skipped or EOFError already printed a warning
            console.print("  [dim]Survey skipped.[/dim]")
            return None
        scores.append(score)

    if not scores:
        return None

    average = sum(scores) / len(scores)

    # Color and message based on score
    if average >= 4.0:
        color = "green"
        label = "Great 💪"
    elif average >= 2.5:
        color = "yellow"
        label = "Moderate 🤔"
    else:
        color = "red"
        label = "At risk ⚠️"

    console.print(
        f"\n  Understanding score: [bold {color}]{average:.1f}/5[/bold {color}] — {label}\n"
    )

    return average
