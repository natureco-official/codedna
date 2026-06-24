"""
Append AI analysis box to CLI command outputs.
Show AI analysis box after each command output.
"""
from rich.panel import Panel
from rich.console import Console
from rich.box import ROUNDED
import sys
from io import StringIO

console = Console()


def print_ai_box(command_name: str, output: str, width: int = 80) -> None:
    """
    Print AI analysis box after command output.

    Args:
        command_name: Command that was run (e.g. "codedna scan")
        output: Command output (raw text)
        width: Panel width
    """
    try:
        from codedna.ai import ai_analyze, is_enabled
    except ImportError:
        return

    if not is_enabled():
        return  # AI is disabled, skip

    # Get AI analysis
    ai_response = ai_analyze(command_name, output)

    if not ai_response:
        return

    # Silently skip on error (AI analysis is optional)
    if ai_response.startswith("AI analysis error"):
        return

    # Color and icon
    border_style = "magenta"
    title = "[bold magenta]🤖 AI Analysis (Pro+)[/bold magenta]"

    # Show maximum 60 lines
    lines = ai_response.strip().split("\n")
    if len(lines) > 60:
        lines = lines[:58] + ["... (truncated)"]
    content = "\n".join(lines)

    panel = Panel(
        content,
        title=title,
        border_style=border_style,
        box=ROUNDED,
        padding=(1, 2),
        width=width,
    )

    console.print()
    console.print(panel)
    console.print()


def capture_and_analyze(command_name: str, run_func, *args, **kwargs) -> None:
    """
    Run a command, capture its output, then show AI analysis.

    Args:
        command_name: Command name (for analysis)
        run_func: Function to run
        *args, **kwargs: Arguments to pass to the function
    """
    # Capture output
    old_stdout = sys.stdout
    sys.stdout = buffer = StringIO()

    try:
        run_func(*args, **kwargs)
    except SystemExit:
        pass
    except Exception as e:
        sys.stdout = old_stdout
        console.print(f"[red]Error: {e}[/red]")
        return
    finally:
        output = buffer.getvalue()
        sys.stdout = old_stdout

    # Show original output
    console.print(output, end="")

    # AI analysis
    print_ai_box(command_name, output)
