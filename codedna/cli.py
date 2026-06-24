"""CodeDNA CLI — typer-based command-line interface."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from codedna import __version__
from codedna.db import (
    get_db_path,
    get_all_file_understanding_scores,
    get_commit_history,
    get_file_scores_for_commit,
    get_latest_commit,
    init_db,
    save_commit,
    save_file_score,
    update_understanding_score,
)
from codedna.git_hook import find_git_root, install_hook, install_ci_workflow, is_hook_installed, uninstall_hook
from codedna.scorer import get_repo, scan_repository, score_latest_commit
from codedna.survey import run_survey

app = typer.Typer(
    name="codedna",
    help="🧬 CodeDNA — AI code transparency tool",
    add_completion=False,
    no_args_is_help=True,
)
console = Console()


def _version_callback(value: bool) -> None:
    """Callback for the --version flag."""
    if value:
        try:
            from importlib.metadata import version as _v
            ver = _v("codedna")
        except Exception:
            ver = "0.2.29"
        console.print(f"codedna {ver}")
        raise typer.Exit()


@app.callback()
def _main_callback(
    version: bool = typer.Option(
        False, "--version", "-V",
        callback=_version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """CodeDNA — root callback."""
    pass


def _get_db(repo_path: Optional[Path] = None) -> Path:
    """Return the repo-specific database path."""
    root = repo_path or find_git_root() or Path.cwd()
    return get_db_path(root)


# ---------------------------------------------------------------------------
# codedna init
# ---------------------------------------------------------------------------
@app.command()
def init(
    repo: Optional[Path] = typer.Option(None, "--repo", "-r", help="Git repo directory"),
    with_ci: bool = typer.Option(False, "--with-ci", help="Also write a GitHub Actions CI template"),
) -> None:
    """Install the git hook, create the database, and optionally write a CI template."""
    console.print()
    console.print(
        Panel.fit(
            "[bold cyan]🧬 CodeDNA[/bold cyan] Setup starting...",
            border_style="cyan",
        )
    )

    # Find repo root
    root = repo or find_git_root()
    if not root:
        console.print("[bold red]Error:[/bold red] Git repo not found. Run 'git init' first.")
        raise typer.Exit(1)

    console.print(f"[dim]Repo root:[/dim] {root}")

    # Initialize database
    db_path = _get_db(root)
    init_db(db_path)
    console.print(f"[green]✓[/green] Database created: [dim]{db_path}[/dim]")

    # Install the hook
    if is_hook_installed(root):
        console.print("[yellow]⚠[/yellow]  Post-commit hook already installed.")
    else:
        if install_hook(root):
            console.print("[green]✓[/green] Post-commit hook installed.")
        else:
            console.print("[red]✗[/red] Hook installation failed.")
            raise typer.Exit(1)

    # CI template
    if with_ci:
        install_ci_workflow(root)

    info = (
        "[bold green]CodeDNA successfully installed![/bold green]\n"
        "Automatic analysis will run after every [bold]git commit[/bold].\n\n"
        "[dim]• Scan the full repo:[/dim] [cyan]codedna scan[/cyan]\n"
        "[dim]• Show latest commit score:[/dim] [cyan]codedna status[/cyan]\n"
        "[dim]• View score history:[/dim] [cyan]codedna history[/cyan]\n"
        "[dim]• Start the API server:[/dim] [cyan]codedna serve[/cyan]\n"
        "[dim]• Generate HTML report:[/dim] [cyan]codedna report[/cyan]"
    )
    if with_ci:
        info += "\n[dim]• CI template:[/dim] [cyan].github/workflows/codedna.yml[/cyan]"

    console.print()
    console.print(Panel(info, border_style="green", padding=(1, 2)))


# ---------------------------------------------------------------------------
# codedna scan
# ---------------------------------------------------------------------------
@app.command()
def scan(
    repo: Optional[Path] = typer.Option(None, "--repo", "-r", help="Git repo directory"),
    max_files: int = typer.Option(200, "--max", "-m", help="Maximum number of files to scan"),
    min_risk: float = typer.Option(0.0, "--min-risk", help="Minimum AI probability filter (0.0-1.0)"),
) -> None:
    """Scan current repo and show AI risk report."""
    console.print()
    console.print("[bold cyan]🧬 CodeDNA[/bold cyan] — Scanning repo...\n")

    root = repo or find_git_root() or Path.cwd()

    with console.status("[dim]Analyzing files...[/dim]"):
        results = scan_repository(root, max_files=max_files)

    if not results:
        console.print("[yellow]No supported files found to scan.[/yellow]")
        console.print("[dim]Supported: .py .js .jsx .ts .tsx[/dim]")
        return

    # Apply min risk filter
    if min_risk > 0:
        results = [s for s in results if s.ai_probability >= min_risk]

    # Sort by AI probability (highest first)
    results.sort(key=lambda s: s.ai_probability, reverse=True)

    # Fetch all file understanding scores in a single query
    db_path = _get_db(root)
    understanding_scores_map: dict[str, float] = {}
    try:
        understanding_scores_map = get_all_file_understanding_scores(db_path=db_path)
    except Exception:
        pass

    # Build table
    table = Table(
        title="",
        border_style="dim",
        show_lines=True,
        header_style="bold",
    )
    table.add_column("File", style="white", min_width=25)
    table.add_column("AI Probability", justify="center", min_width=14)
    table.add_column("Complexity", justify="center", min_width=12)
    table.add_column("Lines", justify="right", min_width=6)
    table.add_column("Understanding", justify="center", min_width=14)

    total_ai = 0.0
    for s in results:
        percentage = int(s.ai_probability * 100)
        ai_text = f"{s.ai_color} %{percentage}"

        if s.complexity_label == "High":
            complexity = "[red]High[/red]"
        elif s.complexity_label == "Medium":
            complexity = "[yellow]Medium[/yellow]"
        else:
            complexity = "[green]Low[/green]"

        # Read understanding score from the single-query map
        understanding_score = understanding_scores_map.get(s.file_path)
        if understanding_score is not None:
            color = "green" if understanding_score >= 4.0 else "yellow" if understanding_score >= 2.5 else "red"
            understanding = f"[{color}]✅ {understanding_score:.1f}/5[/{color}]"
        else:
            understanding = "[dim]⚠️  Unknown[/dim]"

        rel_path = _shorten_path(s.file_path, str(root))

        table.add_row(rel_path, ai_text, complexity, str(s.total_lines), understanding)
        total_ai += s.ai_probability

    console.print(table)

    # Summary line
    avg_ai = (total_ai / len(results)) * 100 if results else 0
    risk_label, risk_color = _risk_label(avg_ai)

    console.print(
        f"\n[bold]Repo Summary:[/bold] {len(results)} files scanned · "
        f"Avg. AI probability: [bold]{avg_ai:.0f}[/bold] · "
        f"Risk: [bold {risk_color}]{risk_label}[/bold {risk_color}]\n"
    )


# ---------------------------------------------------------------------------
# codedna status
# ---------------------------------------------------------------------------
@app.command()
def status(
    repo: Optional[Path] = typer.Option(None, "--repo", "-r", help="Git repo directory"),
    hook: bool = typer.Option(False, "--hook", hidden=True, help="Run in hook mode (ask survey)"),
) -> None:
    """Show last commit score (and ask survey in hook mode)."""
    console.print()
    root = repo or find_git_root() or Path.cwd()
    db_path = _get_db(root)

    # Initialize DB if not exists
    init_db(db_path)

    git_repo = get_repo(root)
    if not git_repo:
        console.print("[bold red]Error:[/bold red] Git repo not found.")
        raise typer.Exit(1)

    with console.status("[dim]Analyzing latest commit...[/dim]"):
        commit_hash, results = score_latest_commit(root)

    if not commit_hash:
        console.print("[yellow]No commits found yet.[/yellow]")
        return

    # Get commit info
    try:
        commit = git_repo.head.commit
        author = f"{commit.author.name}"
        timestamp = int(commit.committed_date)
        message = commit.message.strip().splitlines()[0][:60]
    except Exception:
        author = "Unknown"
        timestamp = 0
        message = ""

    # Survey (hook mode only)
    understanding_score: Optional[float] = None
    if hook:
        understanding_score = run_survey(commit_hash)

    # Save to DB
    save_commit(
        commit_hash=commit_hash,
        author=author,
        timestamp=timestamp,
        files_changed=len(results),
        understanding_score=understanding_score,
        db_path=db_path,
    )
    for s in results:
        save_file_score(
            commit_hash=commit_hash,
            file_path=s.file_path,
            ai_probability=s.ai_probability,
            complexity_score=s.complexity_score,
            comment_ratio=s.comment_ratio,
            understanding_score=understanding_score,
            db_path=db_path,
        )

    # Show summary
    if results:
        avg_ai = sum(s.ai_probability for s in results) / len(results)
        risk_label, risk_color = _risk_label(avg_ai * 100)

        understanding_display = (
            f"[bold green]{understanding_score:.1f}/5[/bold green]"
            if understanding_score is not None
            else "[dim]No survey[/dim]"
        )

        console.print(
            Panel(
                f"[bold]Commit:[/bold] [dim]{commit_hash[:8]}[/dim]  [dim]{message}[/dim]\n"
                f"[bold]Author:[/bold] {author}\n"
                f"[bold]Changed files:[/bold] {len(results)}\n"
                f"[bold]Avg. AI probability:[/bold] [bold {risk_color}]{avg_ai*100:.0f}% ({risk_label})[/bold {risk_color}]\n"
                f"[bold]Understanding score:[/bold] {understanding_display}",
                title="[bold cyan]🧬 CodeDNA — Commit Score[/bold cyan]",
                border_style="cyan",
                padding=(1, 2),
            )
        )
        console.print("[dim]Commit score saved.[/dim]\n")

    # Post-commit hook: check protected module violations and warn (NO blocking)
    if hook:
        try:
            from codedna.protection import show_violation_warnings
            warnings = show_violation_warnings(db_path)
            for warning in warnings:
                console.print(f"[bold red]{warning}[/bold red]")
        except Exception:
            pass  # Never breaks the hook

    else:
        console.print(
            f"[bold]Commit:[/bold] [dim]{commit_hash[:8]}[/dim]\n"
            "[dim]No supported code files found in this commit.[/dim]"
        )


# ---------------------------------------------------------------------------
# codedna history
# ---------------------------------------------------------------------------
@app.command()
def history(
    repo: Optional[Path] = typer.Option(None, "--repo", "-r", help="Git repo directory"),
    limit: int = typer.Option(20, "--limit", "-n", help="Number of commits to show"),
) -> None:
    """Show historical commit scores as a table."""
    console.print()
    root = repo or find_git_root() or Path.cwd()
    db_path = _get_db(root)

    init_db(db_path)
    rows = get_commit_history(limit=limit, db_path=db_path)

    if not rows:
        console.print(
            "[yellow]No commits recorded yet.[/yellow]\n"
            "[dim]Tip: run 'codedna init' to set up, then make a commit.[/dim]"
        )
        return

    table = Table(
        title=f"[bold cyan]🧬 CodeDNA — Last {len(rows)} Commits[/bold cyan]",
        border_style="dim",
        show_lines=True,
        header_style="bold",
    )
    table.add_column("Commit", style="dim", min_width=10)
    table.add_column("Author", min_width=15)
    table.add_column("Date", min_width=17)
    table.add_column("Files", justify="right", min_width=6)
    table.add_column("Understanding", justify="center", min_width=12)

    for row in rows:
        date_str = (
            datetime.fromtimestamp(row["timestamp"]).strftime("%Y-%m-%d %H:%M")
            if row["timestamp"]
            else "?"
        )

        if row["understanding_score"] is not None:
            score = row["understanding_score"]
            if score >= 4.0:
                understanding = f"[green]✅ {score:.1f}/5[/green]"
            elif score >= 2.5:
                understanding = f"[yellow]🔶 {score:.1f}/5[/yellow]"
            else:
                understanding = f"[red]🔴 {score:.1f}/5[/red]"
        else:
            understanding = "[dim]⚠️  None[/dim]"

        table.add_row(
            row["commit_hash"][:8],
            row["author"] or "?",
            date_str,
            str(row["files_changed"] or 0),
            understanding,
        )

    console.print(table)
    console.print()


# ---------------------------------------------------------------------------
# codedna serve
# ---------------------------------------------------------------------------
@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host", help="IP address to listen on"),
    port: int = typer.Option(8000, "--port", "-p", help="Port number"),
    reload: bool = typer.Option(False, "--reload", help="Auto-reload in development mode"),
    repo: Optional[Path] = typer.Option(None, "--repo", "-r", help="Git repo directory"),
) -> None:
    """Start the FastAPI REST server."""
    import os
    import uvicorn

    root = repo or find_git_root() or Path.cwd()
    db_path = _get_db(root)

    # Set environment variables (read by api.py)
    os.environ.setdefault("CODEDNA_REPO_PATH", str(root))
    os.environ.setdefault("CODEDNA_DB_PATH", str(db_path))

    init_db(db_path)

    console.print()
    console.print(
        Panel(
            f"[bold cyan]🧬 CodeDNA API[/bold cyan] starting...\n\n"
            f"[bold]Address:[/bold]  [link]http://{host}:{port}[/link]\n"
            f"[bold]Docs:[/bold]     [link]http://{host}:{port}/docs[/link]\n"
            f"[bold]Repo:[/bold]     [dim]{root}[/dim]\n"
            f"[bold]Database:[/bold] [dim]{db_path}[/dim]\n\n"
            "[dim]Press Ctrl+C to stop[/dim]",
            border_style="cyan",
            padding=(1, 2),
        )
    )

    uvicorn.run(
        "codedna.api:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


# ---------------------------------------------------------------------------
# codedna report
# ---------------------------------------------------------------------------
@app.command()
def report(
    output: Path = typer.Option(Path("codedna-report.html"), "--output", "-o", help="Output file"),
    repo: Optional[Path] = typer.Option(None, "--repo", "-r", help="Git repo directory"),
    open_browser: bool = typer.Option(False, "--open", help="Open report in browser"),
) -> None:
    """Generate HTML report."""
    import webbrowser
    from datetime import datetime
    from codedna.api import _build_html_report

    root = repo or find_git_root() or Path.cwd()
    db_path = _get_db(root)
    init_db(db_path)

    console.print()
    console.print("[bold cyan]🧬 CodeDNA[/bold cyan] — Generating HTML report...\n")

    with console.status("[dim]Analyzing files...[/dim]"):
        results = scan_repository(root, max_files=200)

    results.sort(key=lambda s: s.ai_probability, reverse=True)
    commits = get_commit_history(limit=50, db_path=db_path)

    all_ai = [s.ai_probability for s in results]
    avg_ai = sum(all_ai) / len(all_ai) if all_ai else 0.0
    risk_label, _ = _risk_label(avg_ai * 100)

    understanding_scorelari = [
        float(c["understanding_score"])
        for c in commits
        if c["understanding_score"] is not None
    ]
    avg_understanding = sum(understanding_scorelari) / len(understanding_scorelari) if understanding_scorelari else None

    html = _build_html_report(
        repo_name=root.name,
        total_files=len(results),
        avg_ai=avg_ai,
        risk=risk_label,
        avg_understanding=avg_understanding,
        total_commits=len(commits),
        files=results,
        commits=commits,
        root=root,
    )

    output.write_text(html, encoding="utf-8")
    console.print(f"[green]✓[/green] Report generated: [bold]{output.resolve()}[/bold]")
    console.print(
        f"  [dim]{len(results)} files · "
        f"Avg. AI: {avg_ai*100:.0f}% · "
        f"Risk: {risk_label}[/dim]"
    )

    if open_browser:
        webbrowser.open(output.resolve().as_uri())
        console.print("[dim]Opening in browser...[/dim]")

    console.print()


# ---------------------------------------------------------------------------
# codedna ai-compare
# ---------------------------------------------------------------------------
@app.command(name="ai-compare")
def ai_compare(
    repo: Optional[Path] = typer.Option(None, "--repo", "-r", help="Git repo directory"),
) -> None:
    """Show repo-wide AI tool comparison table."""
    from codedna.ai_fingerprint import compare_tools_in_repo
    from codedna.plan import is_feature_available

    if not is_feature_available("ai_comparison"):
        console.print(
            Panel(
                "[bold yellow]🔒 This feature is available on Enterprise plan.[/bold yellow]\n\n"
                "[dim]To upgrade:[/dim] [cyan]codedna plan activate <LICENSE_KEY>[/cyan]",
                border_style="yellow",
                padding=(1, 2),
            )
        )
        raise typer.Exit(1)

    root = repo or find_git_root() or Path.cwd()
    db_path = _get_db(root)
    init_db(db_path)

    console.print()
    console.print("[bold cyan]🧬 CodeDNA[/bold cyan] — AI tool fingerprint analysis running...\n")
    console.print(
        "[dim]⚠️  This detection is pattern-based estimation — not definitive.[/dim]\n"
    )

    with console.status("[dim]Analyzing files...[/dim]"):
        results = compare_tools_in_repo(root, db_path)

    if not results:
        console.print("[yellow]No files found to analyze.[/yellow]")
        return

    table = Table(border_style="dim", show_lines=True, header_style="bold")
    table.add_column("AI Tool", min_width=12)
    table.add_column("File Count", justify="right", min_width=13)
    table.add_column("Avg. AI Score", justify="right", min_width=13)
    table.add_column("Avg. Understanding", justify="right", min_width=12)

    tool_emojis = {
        "copilot": "🐙", "cursor": "🖱️",
        "claude": "🧠", "unknown": "❓",
    }

    for tool, data in sorted(results.items(), key=lambda x: -x[1].get("file_count", 0)):
        emoji = tool_emojis.get(tool, "🤖")
        understanding = (
            f"{data['avg_understanding']:.1f}/5"
            if data.get("avg_understanding") else "—"
        )
        table.add_row(
            f"{emoji} {tool}",
            str(data.get("file_count", 0)),  # type: ignore
            f"%{data.get('avg_ai_probability', 0) * 100:.0f}",
            understanding,
        )

    console.print(table)
    console.print()


# ---------------------------------------------------------------------------
# codedna onboarding
# ---------------------------------------------------------------------------
@app.command()
def onboarding(
    author: Optional[str] = typer.Option(None, "--author", "-a", help="Single author analysis"),
    team: bool = typer.Option(False, "--team", "-t", help="Team-wide summary"),
    repo: Optional[Path] = typer.Option(None, "--repo", "-r", help="Git repo directory"),
) -> None:
    """Measure developer onboarding speed and show ramp-up curve."""
    from codedna.onboarding import (
        get_author_curve, team_onboarding_summary, get_all_authors,
    )
    from codedna.plan import is_feature_available

    if not is_feature_available("sprint_health"):
        console.print(
            Panel(
                "[bold yellow]🔒 This feature is available on Team plan.[/bold yellow]\n"
                "[dim]To upgrade:[/dim] [cyan]codedna plan activate <LICENSE_KEY>[/cyan]",
                border_style="yellow",
            )
        )
        raise typer.Exit(1)

    root = repo or find_git_root() or Path.cwd()
    db_path = _get_db(root)
    init_db(db_path)

    console.print()

    if team or not author:
        # Team summary
        console.print("[bold cyan]🧬 CodeDNA[/bold cyan] — Onboarding team summary\n")

        with console.status("[dim]Analyzing...[/dim]"):
            summary = team_onboarding_summary(db_path)

        if not summary:
            console.print("[yellow]No authors found.[/yellow]")
            return

        table = Table(
            title="[bold cyan]🚀 Onboarding Summary[/bold cyan]",
            border_style="dim",
            show_lines=True,
            header_style="bold",
        )
        table.add_column("Author", min_width=18)
        table.add_column("Commits", justify="right", min_width=8)
        table.add_column("Surveyed", justify="right", min_width=9)
        table.add_column("Ramp-up", justify="center", min_width=12)
        table.add_column("Latest Understanding", justify="center", min_width=12)

        for y in summary:
            ramp_str = (
                f"{y['ramp_up_weeks']:.1f} weeks"
                if y["ramp_up_weeks"] is not None
                else ("[dim]Insufficient data[/dim]" if not y["sufficient_data"] else "[yellow]Threshold not reached[/yellow]")
            )
            understanding_str = (
                f"{y['latest_avg_understanding']:.1f}/5" if y["latest_avg_understanding"] else "—"
            )
            table.add_row(
                y["author"],
                str(y["total_commits"]),
                str(y["commits_with_understanding"]),
                ramp_str,
                understanding_str,
            )

        console.print(table)

    else:
        # Single author curve
        console.print(f"[bold cyan]🧬 CodeDNA[/bold cyan] — [bold]{author}[/bold] onboarding curve\n")

        with console.status("[dim]Analyzing...[/dim]"):
            curve = get_author_curve(author, db_path)

        if curve.total_commits == 0:
            console.print(f"[yellow]No commits found for author '{author}'.[/yellow]")
            return

        # Ramp-up panel
        ramp_str = (
            f"[green]{curve.ramp_up_weeks:.1f} weeks[/green]"
            if curve.ramp_up_weeks is not None
            else "[yellow]Threshold not yet reached[/yellow]"
            if curve.commits_with_understanding >= 5
            else "[dim]Insufficient data (at least 5 commits needed)[/dim]"
        )

        understanding_str = (
            f"{curve.latest_avg_understanding:.1f}/5" if curve.latest_avg_understanding else "—"
        )

        console.print(
            Panel(
                f"[bold]Author:[/bold] {curve.author}\n"
                f"[bold]Total commits:[/bold] {curve.total_commits}\n"
                f"[bold]Surveyed commits:[/bold] {curve.commits_with_understanding}\n"
                f"[bold]Estimated ramp-up:[/bold] {ramp_str}\n"
                f"[bold]Latest avg. understanding:[/bold] {understanding_str}",
                title="[bold cyan]🚀 Onboarding Analysis[/bold cyan]",
                border_style="cyan",
                padding=(1, 2),
            )
        )

        # Commit-based table (with survey data)
        surveyed = [n for n in curve.points if n.understanding_score is not None]
        if surveyed:
            table = Table(border_style="dim", show_lines=True, header_style="bold")
            table.add_column("#", justify="right", min_width=4)
            table.add_column("Hash", style="dim", min_width=10)
            table.add_column("Date", min_width=12)
            table.add_column("Week", justify="right", min_width=7)
            table.add_column("Understanding", justify="center", min_width=10)

            for n in surveyed:
                score = n.understanding_score or 0.0
                color = "green" if score >= 4 else "yellow" if score >= 2.5 else "red"
                table.add_row(
                    str(n.commit_no),
                    n.commit_hash[:8],
                    n.date.strftime("%Y-%m-%d"),
                    str(n.week_number),
                    f"[{color}]{score:.1f}/5[/{color}]",
                )
            console.print(table)

    console.print()


# ---------------------------------------------------------------------------
# codedna pr-comment
# ---------------------------------------------------------------------------
@app.command(name="pr-comment")
def pr_comment(
    repo: Optional[str] = typer.Option(None, "--repo", help="Repo in owner/repo format (defaults to GITHUB_REPOSITORY env var)"),
    pr: Optional[int] = typer.Option(None, "--pr", help="PR number (auto-detected from event payload if omitted)"),
    rate: float = typer.Option(75.0, "--rate", help="Hourly rate for technical debt"),
) -> None:
    """Post CodeDNA analysis comment to GitHub PR (updates existing comment, no spam)."""
    import os
    from codedna.integrations.github_bot import (
        format_pr_comment, post_or_update_comment, github_actions_pr_infosi,
    )
    from codedna.tech_debt import calculate_repo_debt

    # Token — never logged
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        console.print(
            "[bold red]Error:[/bold red] GITHUB_TOKEN environment variable is not set."
        )
        raise typer.Exit(1)

    # Repo and PR number — parameter first, then GitHub Actions env
    target_repo = repo
    target_pr = pr

    if not target_repo or not target_pr:
        info = github_actions_pr_infosi()
        if info:
            auto_repo, auto_pr = info
            target_repo = target_repo or auto_repo
            target_pr = target_pr or auto_pr

    if not target_repo or not target_pr:
        console.print(
            "[bold red]Error:[/bold red] Repo and PR number not found.\n"
            "[dim]Specify with --repo owner/repo --pr 42 or run inside GitHub Actions.[/dim]"
        )
        raise typer.Exit(1)

    root = find_git_root() or Path.cwd()
    db_path = _get_db(root)
    init_db(db_path)

    console.print(f"\n[bold cyan]🧬 CodeDNA[/bold cyan] — Analyzing PR #{target_pr}...\n")

    with console.status("[dim]Scanning files...[/dim]"):
        from codedna.scorer import scan_repository
        results = scan_repository(root, max_files=200)

    debt_summary_dict: Optional[dict] = None
    try:
        debt = calculate_repo_debt(root, db_path, hourly_rate=rate)
        debt_summary_dict = {
            "total_debt_hours": debt.total_debt_hours,
            "total_monthly_cost_usd": debt.total_monthly_cost_usd,
        }
    except Exception:
        pass

    comment = format_pr_comment(results, debt_summary_dict)

    try:
        result = post_or_update_comment(target_repo, target_pr, comment, token)
        comment_url = result.get("html_url", "")
        console.print(
            f"[green]✓[/green] PR comment posted: [dim]{comment_url}[/dim]\n"
        )
    except RuntimeError as e:
        console.print(f"[bold red]Error:[/bold red] GitHub API request failed: {e}")
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# codedna protect
# ---------------------------------------------------------------------------
protect_app = typer.Typer(help="Protected module management.")
app.add_typer(protect_app, name="protect")


@protect_app.command("add")
def protect_add(
    file_path: str = typer.Argument(..., help="File path to protect"),
    threshold: float = typer.Option(3.5, "--threshold", "-t", help="Minimum understanding score threshold"),
    label: str = typer.Option("", "--label", "-l", help="Human-readable label"),
    repo: Optional[Path] = typer.Option(None, "--repo", "-r", help="Git repo directory"),
) -> None:
    """Mark a file as protected module."""
    from codedna.protection import protect_module
    from codedna.plan import is_feature_available

    if not is_feature_available("bus_factor"):
        console.print("[bold yellow]🔒 This feature is available on Team plan.[/bold yellow]")
        raise typer.Exit(1)

    root = repo or find_git_root() or Path.cwd()
    db_path = _get_db(root)
    init_db(db_path)

    # Convert relative path to absolute
    full_path = str((root / file_path).resolve())
    label = label or file_path
    author = "cli"

    record_id = protect_module(full_path, threshold, label, author, db_path)
    console.print(
        f"[green]✓[/green] Protected module added: [cyan]{file_path}[/cyan]\n"
        f"  [dim]Label:[/dim] {label} · [dim]Threshold:[/dim] {threshold}/5 · [dim]ID:[/dim] #{record_id}"
    )


@protect_app.command("remove")
def protect_remove(
    file_path: str = typer.Argument(..., help="File path to unprotect"),
    repo: Optional[Path] = typer.Option(None, "--repo", "-r", help="Git repo directory"),
) -> None:
    """Remove protection from a file."""
    from codedna.protection import unprotect_module
    from codedna.plan import is_feature_available

    if not is_feature_available("bus_factor"):
        console.print("[bold yellow]🔒 This feature is available on Team plan.[/bold yellow]")
        raise typer.Exit(1)

    root = repo or find_git_root() or Path.cwd()
    db_path = _get_db(root)
    full_path = str((root / file_path).resolve())

    if unprotect_module(full_path, db_path):
        console.print(f"[green]✓[/green] Protection removed: [cyan]{file_path}[/cyan]")
    else:
        console.print(f"[yellow]Not found:[/yellow] '{file_path}' is not in the protected modules list.")


@protect_app.command("list")
def protect_list(
    repo: Optional[Path] = typer.Option(None, "--repo", "-r", help="Git repo directory"),
) -> None:
    """Show all protected modules and their statuses."""
    from codedna.protection import check_protected_modules
    from codedna.plan import is_feature_available

    if not is_feature_available("bus_factor"):
        console.print("[bold yellow]🔒 This feature is available on Team plan.[/bold yellow]")
        raise typer.Exit(1)

    root = repo or find_git_root() or Path.cwd()
    db_path = _get_db(root)
    init_db(db_path)

    modules = check_protected_modules(db_path)
    if not modules:
        console.print("[yellow]No protected modules yet.[/yellow]")
        console.print("[dim]To add one:[/dim] [cyan]codedna protect add <file> --label 'Label'[/cyan]")
        return

    table = Table(
        title="[bold cyan]🛡️ Protected Modules[/bold cyan]",
        border_style="dim", show_lines=True, header_style="bold",
    )
    table.add_column("File", min_width=30)
    table.add_column("Label", min_width=16)
    table.add_column("Threshold", justify="center", min_width=7)
    table.add_column("Current", justify="center", min_width=9)
    table.add_column("Status", justify="center", min_width=12)

    for m in modules:
        current_str = f"{m.current_score:.1f}" if m.current_score is not None else "—"
        if m.status == "VIOLATION":
            status_str = "[bold red]🔴 VIOLATION[/bold red]"
        elif m.status == "SAFE":
            status_str = "[green]✅ SAFE[/green]"
        else:
            status_str = "[dim]⚪ UNKNOWN[/dim]"

        try:
            rel_path = str(Path(m.file_path).relative_to(root))
        except ValueError:
            rel_path = m.file_path[-40:]

        table.add_row(rel_path, m.label, f"{m.threshold:.1f}", current_str, status_str)

    console.print()
    console.print(table)
    console.print()


@protect_app.command("check")
def protect_check(
    repo: Optional[Path] = typer.Option(None, "--repo", "-r", help="Git repo directory"),
) -> None:
    """Show only modules that violated the threshold."""
    from codedna.protection import get_violations
    from codedna.plan import is_feature_available

    if not is_feature_available("bus_factor"):
        console.print("[bold yellow]🔒 This feature is available on Team plan.[/bold yellow]")
        raise typer.Exit(1)

    root = repo or find_git_root() or Path.cwd()
    db_path = _get_db(root)
    init_db(db_path)

    violations = get_violations(db_path)
    if not violations:
        console.print("[green]✅ All protected modules are safe.[/green]")
        return

    console.print()
    for violation in violations:
        score_str = f"{violation.current_score:.1f}" if violation.current_score else "?"
        try:
            rel_path = str(Path(violation.file_path).relative_to(root))
        except ValueError:
            rel_path = violation.file_path
        console.print(
            f"[bold red]⚠️  VIOLATION:[/bold red] [cyan]{rel_path}[/cyan] — "
            f"understanding: [red]{score_str}[/red] < threshold: [yellow]{violation.threshold:.1f}[/yellow] "
            f"([dim]{violation.label}[/dim])"
        )
    console.print()


# ---------------------------------------------------------------------------
# codedna interview
# ---------------------------------------------------------------------------
interview_app = typer.Typer(help="Candidate interview tool.")
app.add_typer(interview_app, name="interview")


@interview_app.command("start")
def interview_start(
    candidate: str = typer.Option(..., "--candidate", "-c", help="Candidate name"),
    difficulty: str = typer.Option("medium", "--difficulty", "-d", help="Difficulty: easy|medium|hard"),
    repo: Optional[Path] = typer.Option(None, "--repo", "-r", help="Git repo directory"),
) -> None:
    """Start new interview session and show anonymized code."""
    from codedna.interview import select_candidate_file, generate_questions, start_session
    from codedna.plan import is_feature_available

    if not is_feature_available("interview_tool"):
        console.print(
            Panel(
                "[bold yellow]🔒 This feature is available on Enterprise plan.[/bold yellow]\n"
                "[dim]To upgrade:[/dim] [cyan]codedna plan activate <LICENSE_KEY>[/cyan]",
                border_style="yellow",
            )
        )
        raise typer.Exit(1)

    root = repo or find_git_root() or Path.cwd()
    db_path = _get_db(root)
    init_db(db_path)

    console.print()
    console.print(
        "[dim]⚠️  This tool does NOT replace human evaluation — it is a supplementary signal.[/dim]\n"
    )

    with console.status("[dim]Selecting a suitable file...[/dim]"):
        file = select_candidate_file(root, db_path, difficulty)

    if not file:
        console.print(f"[yellow]No suitable file found for difficulty '{difficulty}'.[/yellow]")
        raise typer.Exit(1)

    questions = generate_questions(file.anonymized_code)
    session_id = start_session(candidate, file.file_path, questions, db_path)

    console.print(
        Panel(
            f"[bold]Candidate:[/bold] {candidate}\n"
            f"[bold]Difficulty:[/bold] {difficulty} · [dim]Complexity:[/dim] {file.complexity_score:.0f} · [dim]Lines:[/dim] {file.line_count}\n"
            f"[bold]Session ID:[/bold] [cyan]#{session_id}[/cyan]",
            title="[bold cyan]🎯 Interview Started[/bold cyan]",
            border_style="cyan",
            padding=(1, 2),
        )
    )

    console.print("\n[bold]─── Anonymized Code ───[/bold]")
    console.print(f"[dim]{file.anonymized_code[:800]}[/dim]")
    if len(file.anonymized_code) > 800:
        console.print("[dim]... (truncated)[/dim]")

    console.print("\n[bold]─── Questions ───[/bold]")
    for i, question in enumerate(questions, 1):
        console.print(f"  [bold cyan]{i}.[/bold cyan] {question}")

    console.print(
        f"\n[dim]To score:[/dim] [cyan]codedna interview score {session_id} --score 4.0 --notes 'Note'[/cyan]\n"
    )


@interview_app.command("list")
def interview_list(
    repo: Optional[Path] = typer.Option(None, "--repo", "-r", help="Git repo directory"),
    limit: int = typer.Option(10, "--limit", "-n", help="Number of sessions to show"),
) -> None:
    """Show historical interview sessions."""
    from codedna.interview import get_sessions
    from codedna.plan import is_feature_available

    if not is_feature_available("interview_tool"):
        console.print("[bold yellow]🔒 This feature is available on Enterprise plan.[/bold yellow]")
        raise typer.Exit(1)

    root = repo or find_git_root() or Path.cwd()
    db_path = _get_db(root)
    init_db(db_path)

    sessions = get_sessions(db_path, limit=limit)
    if not sessions:
        console.print("[yellow]No interview sessions yet.[/yellow]")
        return

    table = Table(
        title="[bold cyan]🎯 Interview History[/bold cyan]",
        border_style="dim", show_lines=True, header_style="bold",
    )
    table.add_column("#", justify="right", min_width=4)
    table.add_column("Candidate", min_width=16)
    table.add_column("Start Time", min_width=17)
    table.add_column("Score", justify="center", min_width=8)
    table.add_column("Notes", min_width=20)

    for o in sessions:
        score_str = f"{o['skor']:.1f}/5" if o["skor"] is not None else "[dim]—[/dim]"
        table.add_row(
            str(o["id"]),
            o["candidate"] or o.get("aday") or "?",
            o["start_time"] or o.get("start_date") or "?",
            score_str,
            (o["notes"] or o.get("notlar") or "")[:30],
        )

    console.print()
    console.print(table)
    console.print()


@interview_app.command("score")
def interview_score(
    session_id: int = typer.Argument(..., help="Session ID"),
    score: float = typer.Option(..., "--score", "-s", help="Score between 0.0 and 5.0"),
    notes: str = typer.Option("", "--notes", "-n", help="Evaluator notes"),
    repo: Optional[Path] = typer.Option(None, "--repo", "-r", help="Git repo directory"),
) -> None:
    """Add a human review score to an interview session."""
    from codedna.interview import submit_score
    from codedna.plan import is_feature_available

    if not is_feature_available("interview_tool"):
        console.print("[bold yellow]🔒 This feature is available on Enterprise plan.[/bold yellow]")
        raise typer.Exit(1)

    root = repo or find_git_root() or Path.cwd()
    db_path = _get_db(root)

    try:
        result = submit_score(session_id, score, notes, db_path)
        console.print(
            f"[green]✓[/green] Evaluation saved: "
            f"Session [cyan]#{session_id}[/cyan] → [bold]{score:.1f}/5[/bold]"
        )
        if notes:
            console.print(f"  [dim]Note:[/dim] {notes}")
    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# codedna bus-factor
# ---------------------------------------------------------------------------
@app.command(name="bus-factor")
def bus_factor(
    repo: Optional[Path] = typer.Option(None, "--repo", "-r", help="Git repo directory"),
    critical: bool = typer.Option(False, "--critical", "-c", help="Show only critical files (bus_factor=1)"),
    max_files: int = typer.Option(500, "--max", "-m", help="Maximum number of files to process"),
) -> None:
    """Run repo-wide bus factor analysis and show critical ownership risks."""
    from codedna.bus_factor import calculate_bus_factor, get_at_risk_files, _LARGE_REPO_THRESHOLD
    from codedna.plan import is_feature_available

        # Plan check
    if not is_feature_available("bus_factor"):
        console.print(
            Panel(
                "[bold yellow]🔒 This feature is available on Team plan.[/bold yellow]\n"
                "[dim]This feature is available on Team plan.[/dim]\n\n"
                "[dim]To upgrade:[/dim] [cyan]codedna plan activate <LICENSE_KEY>[/cyan]",
                border_style="yellow",
                padding=(1, 2),
            )
        )
        raise typer.Exit(1)

    root = repo or find_git_root() or Path.cwd()
    db_path = _get_db(root)
    init_db(db_path)

    if max_files > _LARGE_REPO_THRESHOLD:
        console.print(
            f"[yellow]⚠[/yellow]  {max_files} files will be scanned — may be slow for large repos."
        )

    console.print()
    console.print("[bold cyan]🧬 CodeDNA[/bold cyan] — Bus Factor analysis running...\n")

    with console.status("[dim]Running git blame...[/dim]"):
        if critical:
            results = get_at_risk_files(root, db_path)
        else:
            results = calculate_bus_factor(root, db_path, max_files=max_files)

    if not results:
        console.print("[yellow]No files found to analyze.[/yellow]")
        return

    # Table
    table = Table(
        title="",
        border_style="dim",
        show_lines=True,
        header_style="bold",
    )
    table.add_column("File", style="white", min_width=30)
    table.add_column("Bus Factor", justify="center", min_width=11)
    table.add_column("Primary Owner", min_width=16)
    table.add_column("Ownership %", justify="right", min_width=11)
    table.add_column("Risk", justify="center", min_width=10)

    critical_count = 0
    for s in results:
        bf_str = str(s.bus_factor)
        if s.risk == "CRITICAL":
            bf_display = f"[red]🚌 {bf_str}[/red]"
            risk_display = "[bold red]CRITICAL[/bold red]"
            critical_count += 1
        elif s.risk == "RISKY":
            bf_display = f"[yellow]🚌 {bf_str}[/yellow]"
            risk_display = "[yellow]RISKY[/yellow]"
        else:
            bf_display = f"[green]🚌 {bf_str}[/green]"
            risk_display = "[green]SAFE[/green]"

        table.add_row(
            s.file_path,
            bf_display,
            s.primary_owner or "?",
            f"%{s.ownership_percentage:.1f}",
            risk_display,
        )

    console.print(table)
    console.print(
        f"\n[bold]Summary:[/bold] {len(results)} files · "
        f"[red]{critical_count} critical[/red] · "
        f"[dim]Threshold: understanding score ≥ 3.5[/dim]\n"
    )


# ---------------------------------------------------------------------------
# codedna debt
# ---------------------------------------------------------------------------
@app.command()
def debt(
    repo: Optional[Path] = typer.Option(None, "--repo", "-r", help="Git repo directory"),
    rate: float = typer.Option(75.0, "--rate", help="Hourly rate ($/hour)"),
    file: Optional[Path] = typer.Option(None, "--file", "-f", help="Single file analysis"),
) -> None:
    """Calculate repo-wide technical debt cost."""
    from codedna.tech_debt import calculate_repo_debt, calculate_file_debt
    from codedna.plan import get_current_plan, Plan

    root = repo or find_git_root() or Path.cwd()
    db_path = _get_db(root)
    init_db(db_path)

    current_plan = get_current_plan()
    dollar_hidden = current_plan == Plan.FREE  # Dollar amounts hidden on Free plan

    console.print()
    console.print("[bold cyan]🧬 CodeDNA[/bold cyan] — Calculating technical debt...\n")

    # Single file mode
    if file:
        # Convert relative path to absolute
        full_file = (root / file).resolve() if not file.is_absolute() else file
        with console.status("[dim]Analyzing...[/dim]"):
            debt = calculate_file_debt(str(full_file), db_path, hourly_rate=rate)

        if not debt:
            console.print(f"[yellow]Warning:[/yellow] No data found for '{file}'.")
            return

        risk_color = {"CRITICAL": "red", "HIGH": "yellow", "MEDIUM": "yellow", "LOW": "green"}.get(
            debt.risk_level, "white"
        )
        cost_str = (
            f"[dim]Pro+ plan required[/dim]"
            if dollar_hidden
            else f"[bold green]${debt.monthly_cost_usd:.2f}/month[/bold green]"
        )

        console.print(
            Panel(
                f"[bold]File:[/bold] [dim]{debt.file_path}[/dim]\n"
                f"[bold]Debt hours:[/bold] {debt.debt_hours:.1f} hours\n"
                f"[bold]Monthly cost:[/bold] {cost_str}\n"
                f"[bold]Risk:[/bold] [{risk_color}]{debt.risk_level}[/{risk_color}]\n"
                f"[bold]AI probability:[/bold] %{debt.ai_probability*100:.0f} · "
                f"[bold]Complexity:[/bold] {debt.complexity:.0f} · "
                f"[bold]Lines:[/bold] {debt.total_lines}",
                title="[bold cyan]💰 Technical Debt — File Detail[/bold cyan]",
                border_style="cyan",
                padding=(1, 2),
            )
        )
        return

    # Repo-wide mode
    with console.status("[dim]Analyzing all files...[/dim]"):
        summary = calculate_repo_debt(root, db_path, hourly_rate=rate)

    cost_str = (
        "[dim]🔒 Pro+ plan required[/dim]"
        if dollar_hidden
        else f"[bold green]${summary.total_monthly_cost_usd:.2f}/month[/bold green]"
    )

    console.print(
        Panel(
            f"[bold]💰 Technical Debt Summary[/bold]\n\n"
            f"[bold]Total estimated debt:[/bold] [cyan]{summary.total_debt_hours:.1f} hours[/cyan]\n"
            f"[bold]Monthly cost:[/bold] {cost_str}\n"
            f"[bold]Hourly rate:[/bold] [dim]${rate:.0f}/hour[/dim]\n"
            f"[bold]Files analyzed:[/bold] {summary.total_files}",
            border_style="cyan",
            padding=(1, 2),
        )
    )

    if summary.top_5_most_expensive:
        console.print("[bold]Top 5 most expensive files:[/bold]")
        table = Table(border_style="dim", show_lines=True, header_style="bold")
        table.add_column("File", style="white", min_width=30)
        table.add_column("Debt Hours", justify="right", min_width=11)
        table.add_column("Monthly", justify="right", min_width=10)
        table.add_column("Risk", justify="center", min_width=10)

        for d in summary.top_5_most_expensive:
            risk_color = {
                "CRITICAL": "red", "HIGH": "yellow", "MEDIUM": "yellow", "LOW": "green",
            }.get(d.risk_level, "white")

            monthly = (
                "[dim]hidden[/dim]"
                if dollar_hidden
                else f"[{risk_color}]${d.monthly_cost_usd:.2f}[/{risk_color}]"
            )

            # Shorten file path
            try:
                rel_path = str(Path(d.file_path).relative_to(root))
            except ValueError:
                rel_path = d.file_path[-40:]

            table.add_row(
                rel_path,
                f"{d.debt_hours:.1f} h",
                monthly,
                f"[{risk_color}]{d.risk_level}[/{risk_color}]",
            )
        console.print(table)

    if dollar_hidden:
        console.print(
            "\n[dim]💡 Dollar amounts are visible on Pro+: [cyan]codedna plan activate <KEY>[/cyan][/dim]\n"
        )
    else:
        console.print()


# ---------------------------------------------------------------------------
# codedna sprint
# ---------------------------------------------------------------------------
sprint_app = typer.Typer(help="Sprint management and health score.")
app.add_typer(sprint_app, name="sprint")


@sprint_app.command("create")
def sprint_create(
    name: str = typer.Option(..., "--name", "-n", help="Sprint name"),
    start: str = typer.Option(..., "--start", "-s", help="Start date (YYYY-MM-DD)"),
    end: str = typer.Option(..., "--end", "-e", help="End date (YYYY-MM-DD)"),
    repo: Optional[Path] = typer.Option(None, "--repo", "-r", help="Git repo directory"),
) -> None:
    """Create a new sprint and calculate the health score."""
    from datetime import datetime as dt
    from codedna.sprint_health import calculate_sprint_health, save_sprint_result
    from codedna.plan import is_feature_available

    if not is_feature_available("sprint_health"):
        console.print(
            Panel(
                "[bold yellow]🔒 This feature is available on Team plan.[/bold yellow]\n"
                "[dim]This feature is available on Team plan.[/dim]\n\n"
                "[dim]To upgrade:[/dim] [cyan]codedna plan activate <LICENSE_KEY>[/cyan]",
                border_style="yellow",
                padding=(1, 2),
            )
        )
        raise typer.Exit(1)

    # Parse dates
    try:
        start_date = dt.fromisoformat(start)
        end_date = dt.fromisoformat(end)
    except ValueError:
        console.print(f"[bold red]Error:[/bold red] Invalid date format. Usage: YYYY-MM-DD")
        raise typer.Exit(1)

    if end_date <= start_date:
        console.print("[bold red]Error:[/bold red] End date must be after start date.")
        raise typer.Exit(1)

    root = repo or find_git_root() or Path.cwd()
    db_path = _get_db(root)
    init_db(db_path)

    console.print()
    console.print(f"[bold cyan]🧬 CodeDNA[/bold cyan] — [bold]{name}[/bold] sprint analysis running...\n")

    with console.status("[dim]Analyzing commits...[/dim]"):
        result = calculate_sprint_health(root, db_path, start_date, end_date, name)

    sprint_id = save_sprint_result(result, db_path)

    status_color = {
        "HEALTHY": "green", "WARNING": "yellow", "RISKY": "red",
    }.get(result.status, "white")

    console.print(
        Panel(
            f"[bold]Sprint:[/bold] {result.sprint_name}\n"
            f"[bold]Date:[/bold] {start} → {end}\n"
            f"[bold]Health Score:[/bold] [{status_color}]{result.health_score:.1f}/100 ({result.status})[/{status_color}]\n"
            f"[bold]Total Commits:[/bold] {result.total_commits}\n"
            f"[bold]Avg. Understanding:[/bold] {f'{result.avg_understanding:.1f}/5' if result.avg_understanding else 'No data'}\n"
            f"[bold]AI Ratio:[/bold] {result.ai_ratio * 100:.0f}% high risk\n"
            f"[bold]Debt Delta:[/bold] {result.debt_delta_hours:.1f} h/commit",
            title=f"[bold cyan]🏃 Sprint Health Report — #{sprint_id}[/bold cyan]",
            border_style=status_color,
            padding=(1, 2),
        )
    )
    console.print(f"[dim]Sprint #{sprint_id} saved.[/dim]\n")


@sprint_app.command("health")
def sprint_health(
    repo: Optional[Path] = typer.Option(None, "--repo", "-r", help="Git repo directory"),
) -> None:
    """Show the latest sprint health score."""
    from codedna.db import get_latest_sprint
    from codedna.plan import is_feature_available

    if not is_feature_available("sprint_health"):
        console.print(
            Panel(
                "[bold yellow]🔒 This feature is available on Team plan.[/bold yellow]\n"
                "[dim]To upgrade:[/dim] [cyan]codedna plan activate <LICENSE_KEY>[/cyan]",
                border_style="yellow",
            )
        )
        raise typer.Exit(1)

    root = repo or find_git_root() or Path.cwd()
    db_path = _get_db(root)
    init_db(db_path)

    sprint = get_latest_sprint(db_path=db_path)
    if not sprint:
        console.print("[yellow]No sprints recorded yet.[/yellow]")
        console.print("[dim]To create one:[/dim] [cyan]codedna sprint create --name 'Sprint 1' --start 2026-06-01 --end 2026-06-14[/cyan]")
        return

    score = sprint["health_score"] or 0.0
    status = "HEALTHY" if score >= 80 else "WARNING" if score >= 50 else "RISKY"
    status_color = {"HEALTHY": "green", "WARNING": "yellow", "RISKY": "red"}[status]

    from datetime import datetime as dt
    start_str = dt.fromtimestamp(sprint["start_date"]).strftime("%Y-%m-%d") if sprint["start_date"] else "?"
    end_str = dt.fromtimestamp(sprint["end_date"]).strftime("%Y-%m-%d") if sprint["end_date"] else "?"

    understanding_val = sprint["avg_understanding"]
    understanding_str = f"{understanding_val:.1f}/5" if understanding_val else "No data"
    delta_val = sprint["debt_delta_hours"] or 0.0

    console.print()
    console.print(
        Panel(
            f"[bold]Sprint:[/bold] {sprint['sprint_name']}\n"
            f"[bold]Date:[/bold] {start_str} → {end_str}\n"
            f"[bold]Health Score:[/bold] [{status_color}]{score:.1f}/100 ({status})[/{status_color}]\n"
            f"[bold]Avg. Understanding:[/bold] {understanding_str}\n"
            f"[bold]Debt Delta:[/bold] {delta_val:.1f} h/commit",
            title="[bold cyan]🏃 Latest Sprint Health[/bold cyan]",
            border_style=status_color,
            padding=(1, 2),
        )
    )


@sprint_app.command("history")
def sprint_history(
    repo: Optional[Path] = typer.Option(None, "--repo", "-r", help="Git repo directory"),
    limit: int = typer.Option(10, "--limit", "-n", help="Number of sprints to show"),
) -> None:
    """Show past sprints as a table."""
    from codedna.db import get_sprint_history as db_sprint_history
    from codedna.plan import is_feature_available
    from datetime import datetime as dt

    if not is_feature_available("sprint_health"):
        console.print("[bold yellow]🔒 This feature is available on Team plan.[/bold yellow]")
        raise typer.Exit(1)

    root = repo or find_git_root() or Path.cwd()
    db_path = _get_db(root)
    init_db(db_path)

    sprints = db_sprint_history(limit=limit, db_path=db_path)
    if not sprints:
        console.print("[yellow]No sprints recorded yet.[/yellow]")
        return

    table = Table(
        title=f"[bold cyan]🏃 Sprint History — Last {len(sprints)}[/bold cyan]",
        border_style="dim",
        show_lines=True,
        header_style="bold",
    )
    table.add_column("Sprint", min_width=16)
    table.add_column("Date Range", min_width=22)
    table.add_column("Health", justify="center", min_width=14)
    table.add_column("Understanding", justify="center", min_width=10)
    table.add_column("Debt Delta", justify="right", min_width=11)

    for s in sprints:
        score = s["health_score"] or 0.0
        status = "HEALTHY" if score >= 80 else "WARNING" if score >= 50 else "RISKY"
        color = {"HEALTHY": "green", "WARNING": "yellow", "RISKY": "red"}[status]

        start_str = dt.fromtimestamp(s["start_date"]).strftime("%Y-%m-%d") if s["start_date"] else "?"
        end_str = dt.fromtimestamp(s["end_date"]).strftime("%Y-%m-%d") if s["end_date"] else "?"

        understanding_str = f"{s['avg_understanding']:.1f}/5" if s["avg_understanding"] else "—"
        delta_str = f"{s['debt_delta_hours']:.1f}h" if s["debt_delta_hours"] else "—"

        table.add_row(
            s["sprint_name"] or "?",
            f"{start_str} → {end_str}",
            f"[{color}]{score:.0f}/100 {status}[/{color}]",
            understanding_str,
            delta_str,
        )

    console.print()
    console.print(table)
    console.print()


# ---------------------------------------------------------------------------
# codedna plan
# ---------------------------------------------------------------------------
@app.command()
def plan(
    command: Optional[str] = typer.Argument(
        None,
        help="'activate' or direct license key",
    ),
    key: Optional[str] = typer.Argument(
        None,
        help="License key (used with activate)",
    ),
) -> None:
    """Show current plan or activate a plan with a license key.

    Usage:
      codedna plan                       # show current plan
      codedna plan activate <KEY>        # activate license
      codedna plan <KEY>                 # shortcut
    """
    from codedna.plan import (
        Plan as PlanEnum,
        get_current_plan,
        activate_license,
        get_plan_limits,
    )

    # Support "activate <KEY>" or direct "<KEY>" syntax
    license_key: Optional[str] = None
    if command == "activate" and key:
        license_key = key
    elif command and command != "activate":
        license_key = command

    if license_key:
        # Activate license
        try:
            activated_plan = activate_license(license_key)
            console.print(
                Panel(
                    f"[bold green]✓ License activated![/bold green]\n\n"
                    f"[bold]Plan:[/bold] [cyan]{activated_plan.value.upper()}[/cyan]\n"
                    f"[bold]Key:[/bold] [dim]{license_key[:12]}...[/dim]",
                    border_style="green",
                    padding=(1, 2),
                )
            )
        except ValueError as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
            raise typer.Exit(1)
        return

    # Show current plan
    current = get_current_plan()
    limits = get_plan_limits()

    plan_color = {
        PlanEnum.FREE: "dim",
        PlanEnum.PRO: "cyan",
        PlanEnum.TEAM: "green",
        PlanEnum.ENTERPRISE: "yellow",
    }.get(current, "white")

    table = Table(border_style="dim", show_header=False, padding=(0, 1))
    table.add_column("Feature", style="dim")
    table.add_column("Value", style="white")

    for k, v in limits.items():
        if isinstance(v, bool):
            display = "[green]✓[/green]" if v else "[red]✗[/red]"
        elif isinstance(v, int) and v == -1:
            display = "[dim]Unlimited[/dim]"
        else:
            display = str(v)
        table.add_row(k.replace("_", " ").title(), display)

    console.print()
    console.print(
        Panel(
            f"[bold]Current Plan:[/bold] [{plan_color}]{current.value.upper()}[/{plan_color}]\n\n"
            + (
                "[dim]To activate a license:[/dim] [cyan]codedna plan activate <LICENSE_KEY>[/cyan]"
                if current == PlanEnum.FREE
                else "[dim]To upgrade:[/dim] [cyan]codedna plan activate <LICENSE_KEY>[/cyan]"
            ),
            title="[bold cyan]🧬 CodeDNA Plan[/bold cyan]",
            border_style="cyan",
            padding=(1, 2),
        )
    )
    console.print(table)
    console.print()


# ---------------------------------------------------------------------------
# codedna dashboard
# ---------------------------------------------------------------------------
@app.command()
def dashboard(
    api_port: int = typer.Option(8000, "--api-port", help="FastAPI port number"),
    ui_port: int = typer.Option(3000, "--ui-port", help="Next.js dashboard port number"),
    repo: Optional[Path] = typer.Option(None, "--repo", "-r", help="Git repo directory"),
) -> None:
    """Start FastAPI + Next.js dashboard and open in browser."""
    import os
    import subprocess
    import time
    import webbrowser

    root = repo or find_git_root() or Path.cwd()
    db_path = _get_db(root)
    init_db(db_path)

    # Find the dashboard/ folder — relative to CLI location or CWD
    dashboard_paths = [
        Path(__file__).parent.parent / "dashboard",
        Path.cwd() / "dashboard",
        root / "dashboard",
    ]
    dashboard_root = next((p for p in dashboard_paths if (p / "package.json").exists()), None)

    if not dashboard_root:
        console.print(
            "[bold red]Error:[/bold red] dashboard/ folder not found.\n"
            "[dim]A 'dashboard/' folder must exist in the codedna project root.[/dim]"
        )
        raise typer.Exit(1)

    console.print()
    console.print(
        Panel(
            f"[bold cyan]🧬 CodeDNA Dashboard[/bold cyan] starting...\n\n"
            f"[bold]API:[/bold]       [link]http://localhost:{api_port}[/link]\n"
            f"[bold]Dashboard:[/bold] [link]http://localhost:{ui_port}[/link]\n\n"
            "[dim]Press Ctrl+C to stop[/dim]",
            border_style="cyan",
            padding=(1, 2),
        )
    )

    # Set environment variables
    env = os.environ.copy()
    env["CODEDNA_REPO_PATH"] = str(root)
    env["CODEDNA_DB_PATH"] = str(db_path)
    env["NEXT_PUBLIC_API_URL"] = f"http://localhost:{api_port}"

    # Start FastAPI process — use venv Python
    import sys
    python_bin = sys.executable

    api_proc = subprocess.Popen(
        [
            python_bin, "-m", "uvicorn",
            "codedna.api:app",
            "--host", "127.0.0.1",
            "--port", str(api_port),
        ],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Start Next.js dev server — call node_modules/.bin/next directly
    next_bin = dashboard_root / "node_modules" / ".bin" / "next"
    npm_cmd = str(next_bin) if next_bin.exists() else "npm"
    ui_cmd = (
        [npm_cmd, "dev", "--port", str(ui_port)]
        if next_bin.exists()
        else ["npm", "run", "dev", "--", "--port", str(ui_port)]
    )
    ui_proc = subprocess.Popen(
        ui_cmd,
        cwd=str(dashboard_root),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Wait for startup, then open browser
    console.print("[dim]Starting servers...[/dim]")
    time.sleep(4)

    try:
        webbrowser.open(f"http://localhost:{ui_port}")
        console.print(f"[green]✓[/green] Browser opened: [link]http://localhost:{ui_port}[/link]")
        console.print("[dim]Press Ctrl+C to stop[/dim]\n")

        # Wait for both processes
        api_proc.wait()
    except KeyboardInterrupt:
        console.print("\n[yellow]Shutting down...[/yellow]")
    finally:
        # Clean up both processes
        for proc in [api_proc, ui_proc]:
            try:
                proc.terminate()
                proc.wait(timeout=3)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        console.print("[dim]CodeDNA stopped.[/dim]")


# ---------------------------------------------------------------------------
# codedna uninstall (bonus)
# ---------------------------------------------------------------------------
@app.command()
def uninstall(
    repo: Optional[Path] = typer.Option(None, "--repo", "-r", help="Git repo directory"),
) -> None:
    """Remove CodeDNA hook."""
    root = repo or find_git_root()
    if uninstall_hook(root):
        console.print("[green]✓[/green] CodeDNA uninstalled.")
    else:
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# codedna doctor (system health check)
# ---------------------------------------------------------------------------
@app.command()
def doctor(
    fix: bool = typer.Option(False, "--fix", help="Attempt to auto-fix detected issues"),
    repo: Optional[Path] = typer.Option(None, "--repo", "-r", help="Git repo directory"),
) -> None:
    """Run a system health check (Python, Git, tree-sitter, DB, hook, API, network)."""

    console.print()
    console.print(
        Panel.fit(
            "[bold cyan]🧬 CodeDNA — System Health Check[/bold cyan]\n"
            f"[dim]Version: {__version__} · Plan: detecting...[/dim]",
            border_style="cyan",
            padding=(1, 4),
        )
    )
    console.print()

    issues: list[str] = []
    warnings: list[str] = []
    checks: list[tuple[str, str, str]] = []  # (category, status, message)

    def _record(category: str, status: str, message: str) -> None:
        """status: 'ok' | 'warn' | 'fail'"""
        checks.append((category, status, message))
        if status == "fail":
            issues.append(f"{category}: {message}")
        elif status == "warn":
            warnings.append(f"{category}: {message}")

    with console.status("[bold cyan]🔍 Running health checks...[/bold cyan]", spinner="dots"):
        import subprocess

        # 1. Python Environment
        py_ver = sys.version_info
        if py_ver >= (3, 10):
            _record("Python", "ok", f"{py_ver.major}.{py_ver.minor}.{py_ver.micro} (≥ 3.10 required)")
        else:
            _record("Python", "fail", f"{py_ver.major}.{py_ver.minor}.{py_ver.micro} — 3.10+ required")

        # 2. CodeDNA installation
        try:
            import codedna
            _record("CodeDNA", "ok", f"v{codedna.__version__} at {Path(codedna.__file__).parent}")
        except Exception as e:
            _record("CodeDNA", "fail", f"import failed: {e}")

        # 3. Git
        try:
            result = subprocess.run(["git", "--version"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                _record("Git", "ok", result.stdout.strip())
            else:
                _record("Git", "fail", "git command returned non-zero")
        except FileNotFoundError:
            _record("Git", "fail", "git not found on PATH")
        except Exception as e:
            _record("Git", "warn", f"check failed: {e}")

        # 4. Tree-sitter parsers
        parsers = [
            ("tree_sitter", "tree-sitter"),
            ("tree_sitter_python", "tree-sitter-python"),
            ("tree_sitter_javascript", "tree-sitter-javascript"),
            ("tree_sitter_typescript", "tree-sitter-typescript"),
        ]
        for mod_name, pkg_name in parsers:
            try:
                __import__(mod_name)
                _record("Tree-sitter", "ok", pkg_name)
            except ImportError:
                _record("Tree-sitter", "fail", f"{pkg_name} not installed")

        # 5. Database
        db_status = "skip"
        db_msg = "Not in a git repo"
        db_path: Optional[Path] = None
        try:
            root = repo or find_git_root()
            db_path = get_db_path(root)
            if db_path.exists():
                size_kb = db_path.stat().st_size / 1024
                _record("Database", "ok", f"{db_path} ({size_kb:.1f} KB)")
                db_status = "ok"
                db_msg = f"{db_path} ({size_kb:.1f} KB)"
            else:
                _record("Database", "warn", f"no database at {db_path}")
                db_status = "warn"
                db_msg = "not initialized"
                if fix:
                    try:
                        init_db(db_path)
                        _record("Database", "ok", "initialized (auto-fixed)")
                        db_status = "ok"
                        db_msg = "auto-fixed"
                    except Exception as e:
                        _record("Database", "fail", f"auto-init failed: {e}")
        except Exception:
            _record("Database", "warn", "skipped (not in a git repo)")

        # 6. Git hook
        try:
            root = repo or find_git_root()
            if is_hook_installed(root):
                _record("Hook", "ok", "post-commit hook installed")
            else:
                _record("Hook", "warn", "post-commit hook not installed")
                if fix:
                    try:
                        install_hook(root)
                        _record("Hook", "ok", "installed (auto-fixed)")
                    except Exception as e:
                        _record("Hook", "fail", f"auto-install failed: {e}")
        except Exception:
            _record("Hook", "warn", "skipped (not in a git repo)")

        # 7. Core dependencies
        deps = [
            ("typer", "CLI framework"),
            ("rich", "Terminal UI"),
            ("gitpython", "Git integration"),
            ("fastapi", "REST API"),
            ("uvicorn", "ASGI server"),
            ("pydantic", "Data validation"),
            ("pyjwt", "JWT auth"),
            ("bcrypt", "Password hashing"),
        ]
        for mod_name, desc in deps:
            try:
                m = __import__(mod_name)
                ver = getattr(m, "__version__", "?")
                _record("Dependencies", "ok", f"{mod_name} {ver} — {desc}")
            except ImportError:
                _record("Dependencies", "fail", f"{mod_name} not installed — {desc}")

        # 8. License & Plan
        license_path = Path.home() / ".codedna" / "license.json"
        if license_path.exists():
            try:
                import json
                with open(license_path) as f:
                    lic = json.load(f)
                plan = lic.get("plan", "free")
                _record("License", "ok", f"plan = {plan.upper()}")
            except Exception as e:
                _record("License", "warn", f"file unreadable: {e}")
        else:
            _record("License", "warn", f"no license at {license_path} (FREE plan)")

        # 9. Network
        try:
            import urllib.request
            urllib.request.urlopen("https://pypi.org/pypi/codedna/json", timeout=5)
            _record("Network", "ok", "PyPI reachable")
        except Exception as e:
            _record("Network", "warn", f"PyPI unreachable: {type(e).__name__}")

    # ─── Render results as a beautiful table ────────────────────────────
    status_emoji = {"ok": "[green]✓[/green]", "warn": "[yellow]⚠[/yellow]", "fail": "[red]✗[/red]", "skip": "[dim]–[/dim]"}

    table = Table(
        border_style="dim",
        show_lines=True,
        header_style="bold cyan",
        title="[bold]Health Check Results[/bold]",
        title_style="bold white",
    )
    table.add_column("Category", style="bold white", min_width=14)
    table.add_column("Status", justify="center", min_width=7)
    table.add_column("Details", style="white")

    current_cat = None
    for cat, status, msg in checks:
        emoji = status_emoji.get(status, "[dim]?[/dim]")
        table.add_row(cat, emoji, msg)
        current_cat = cat

    console.print(table)
    console.print()

    # ─── Summary panel ──────────────────────────────────────────────────
    n_ok = sum(1 for _, s, _ in checks if s == "ok")
    n_warn = sum(1 for _, s, _ in checks if s == "warn")
    n_fail = sum(1 for _, s, _ in checks if s == "fail")
    total = len(checks)

    if n_fail == 0 and n_warn == 0:
        border = "green"
        title = "[bold green]✓ All checks passed — system healthy[/bold green]"
        body = f"[green]{n_ok}/{total} checks passed. CodeDNA is ready to use.[/green]\n\n[dim]Run [bold]codedna scan[/bold] in a git repo to get started.[/dim]"
    elif n_fail == 0:
        border = "yellow"
        title = f"[bold yellow]⚠ {n_warn} warning(s) — system functional with caveats[/bold yellow]"
        body = f"[yellow]{n_ok}/{total} checks passed, {n_warn} warning(s).[/yellow]\n\n[dim]Run [bold]codedna doctor --fix[/bold] to attempt auto-fixes.[/dim]"
    else:
        border = "red"
        title = f"[bold red]✗ {n_fail} critical issue(s) — fix required[/bold red]"
        body = f"[red]{n_fail} critical, {n_warn} warning, {n_ok} passed (out of {total}).[/red]\n\n[dim]Re-run [bold]codedna doctor --fix[/bold] or install missing dependencies.[/dim]"

    console.print(
        Panel(
            body,
            title=title,
            border_style=border,
            padding=(1, 2),
        )
    )

    if n_fail > 0:
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# codedna update (self-upgrade from PyPI)
# ---------------------------------------------------------------------------
@app.command()
def update(
    check_only: bool = typer.Option(False, "--check", "-c", help="Only check for updates, do not install"),
    target: Optional[str] = typer.Option(None, "--target", "-t", help="Install a specific version (e.g. 0.3.2)"),
) -> None:
    """Check for updates and upgrade CodeDNA to the latest PyPI release."""
    import json
    import urllib.request
    import urllib.error

    console.print(Panel.fit("🧬 CodeDNA — Update Check", style="bold cyan"))
    console.print()

    # 1. Get current version
    import codedna
    current = codedna.__version__
    console.print(f"  Current version: [bold]{current}[/bold]")

    # 2. Fetch latest version from PyPI
    try:
        req = urllib.request.Request(
            "https://pypi.org/pypi/codedna/json",
            headers={"Accept": "application/json", "User-Agent": "codedna-updater"},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
    except Exception as e:
        console.print(f"  [red]✗[/red] Could not reach PyPI: {e}")
        raise typer.Exit(1)

    latest = data["info"]["version"]
    desired = target or latest
    console.print(f"  Latest version : [bold]{latest}[/bold]")

    if target:
        console.print(f"  Target version : [bold]{target}[/bold]")

    # 3. Compare
    def _parse(v: str) -> tuple[int, ...]:
        return tuple(int(x) for x in v.split(".") if x.isdigit())

    if _parse(current) >= _parse(desired) and not target:
        console.print()
        console.print(Panel(
            f"[bold green]✓ Already on the latest version.[/bold green]\n\n"
            f"[dim]Current:[/dim] [cyan]{current}[/cyan]\n"
            f"[dim]Latest:[/dim]  [cyan]{latest}[/cyan]",
            title="[bold green]🧬 CodeDNA — Up to date[/bold green]",
            border_style="green",
            padding=(1, 2),
        ))
        console.print()
        return

    console.print()
    if check_only:
        console.print(Panel(
            f"[bold yellow]⚠ Update available[/bold yellow]\n\n"
            f"[dim]Current:[/dim] [yellow]{current}[/yellow]  →  [dim]Latest:[/dim] [green]{latest}[/green]",
            title="[bold yellow]🧬 CodeDNA — Update Check[/bold yellow]",
            border_style="yellow",
            padding=(1, 2),
        ))
        console.print(f"  [dim]Run [bold]codedna update[/bold] to install.[/dim]")
        console.print()
        return

    # 4. Detect installer (uv > pip)
    import shutil
    import subprocess

    use_uv = shutil.which("uv") is not None
    if use_uv:
        cmd = ["uv", "tool", "install", "--force", f"codedna=={desired}"]
        label = "uv tool install --force"
    else:
        cmd = [sys.executable, "-m", "pip", "install", "--upgrade", f"codedna=={desired}"]
        label = "pip install --upgrade"

    console.print(f"  [cyan]→[/cyan] Running: {label} codedna=={desired}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        console.print("  [red]✗[/red] Install timed out after 120s")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"  [red]✗[/red] Install failed: {e}")
        raise typer.Exit(1)

    if result.returncode != 0:
        console.print(f"  [red]✗[/red] Install returned exit code {result.returncode}")
        if result.stderr:
            # Show last 10 lines of stderr
            for line in result.stderr.strip().split("\n")[-10:]:
                console.print(f"    [dim]{line}[/dim]")
        raise typer.Exit(1)

    # 5. Verify new version
    try:
        # Re-import to get fresh metadata
        import importlib
        importlib.reload(codedna)
        new_ver = codedna.__version__
    except Exception:
        new_ver = "?"

    console.print()
    if new_ver == desired:
        console.print()
        console.print(Panel(
            f"[bold green]✓ Updated {current} → {new_ver}[/bold green]\n\n"
            f"[dim]Installer:[/dim] [cyan]{label}[/cyan]\n"
            f"[dim]Config:[/dim]    [dim]{'chmod 644 token removed' if 'github' in label else '~/.codedna/ai_config.json'}[/dim]",
            title="[bold green]🧬 CodeDNA — Update Complete[/bold green]",
            border_style="green",
            padding=(1, 2),
        ))
        console.print()
    else:
        console.print()
        console.print(Panel(
            f"[bold green]✓ Update complete.[/bold green]\n\n"
            f"[dim]Installed:[/dim] [green]{desired}[/green]\n"
            f"[dim]Current process shows:[/dim] [yellow]{new_ver}[/yellow]\n\n"
            f"[yellow]Restart your shell to pick up the new binary.[/yellow]",
            title="[bold green]🧬 CodeDNA — Update Complete[/bold green]",
            border_style="green",
            padding=(1, 2),
        ))
        console.print()


# ---------------------------------------------------------------------------
# codedna setup (interactive AI analysis configuration wizard)
# ---------------------------------------------------------------------------
@app.command()
def setup(
    reset: bool = typer.Option(False, "--reset", help="Clear existing AI config and reconfigure"),
    show: bool = typer.Option(False, "--show", help="Show current AI configuration"),
) -> None:
    """Configure AI analysis provider, API key, and model."""
    from codedna.ai import AIConfig, AI_CONFIG_PATH, PROVIDERS, DEFAULT_MODELS, ai_analyze

    # ── --show: just display current config ────────────────────────────
    if show:
        cfg = AIConfig.load()
        if not cfg:
            console.print()
            console.print(Panel(
                "[yellow]⚠  No AI configuration found.[/yellow]\n\n"
                "Run [bold cyan]codedna setup[/bold cyan] to create one.",
                border_style="yellow",
                padding=(1, 2),
            ))
            console.print()
            return
        console.print()
        table = Table(
            title="[bold cyan]🧬 CodeDNA — AI Configuration[/bold cyan]",
            title_style="bold white",
            border_style="cyan",
            show_lines=True,
            header_style="bold cyan",
            padding=(0, 2),
        )
        table.add_column("Field", style="bold white", min_width=14)
        table.add_column("Value", style="white")
        table.add_row("[bold]Provider[/bold]", f"[cyan]{cfg.provider}[/cyan]")
        table.add_row("[bold]Model[/bold]", f"[cyan]{cfg.model}[/cyan]")
        api_display = f"{cfg.api_key[:8]}…{cfg.api_key[-4:]}" if len(cfg.api_key) > 12 else "(set)"
        table.add_row("[bold]API key[/bold]", f"[dim]{api_display}[/dim]")
        status_str = "[green]✓ enabled[/green]" if cfg.enabled else "[yellow]⚠ disabled[/yellow]"
        table.add_row("[bold]Status[/bold]", status_str)
        table.add_row("[bold]Config file[/bold]", f"[dim]{AI_CONFIG_PATH}[/dim]")
        console.print(table)

        # ── Status panel ──────────────────────────────────────────────
        if cfg.enabled and cfg.api_key:
            border = "green"
            body = (
                f"[green]✓ AI analysis is active.[/green]\n"
                f"[dim]Provider {cfg.provider} will be used for commit interpretation.[/dim]"
            )
            title = "[bold green]✓ AI Ready[/bold green]"
        elif cfg.enabled and not cfg.api_key:
            border = "yellow"
            body = "[yellow]⚠ Enabled but no API key set — calls will fail.[/yellow]"
            title = "[bold yellow]⚠ Incomplete[/bold yellow]"
        else:
            border = "yellow"
            body = "[yellow]⚠ AI analysis is disabled.[/yellow]\n[dim]Re-run with [bold]codedna setup --reset[/bold].[/dim]"
            title = "[bold yellow]⚠ Disabled[/bold yellow]"

        console.print()
        console.print(Panel(body, title=title, border_style=border, padding=(1, 2)))
        console.print()
        return

    # ── Welcome panel ──────────────────────────────────────────────────
    console.print()
    console.print(
        Panel.fit(
            "[bold cyan]🧬 CodeDNA — Setup Wizard[/bold cyan]\n"
            "[dim]Configure AI analysis for commit interpretation.[/dim]",
            border_style="cyan",
            padding=(1, 4),
        )
    )
    console.print()

    # ── --reset: clear existing ───────────────────────────────────────
    existing = AIConfig.load()
    if existing and not reset:
        console.print(
            Panel(
                f"[yellow]Existing configuration found:[/yellow]\n"
                f"  Provider : {existing.provider}\n"
                f"  Model    : {existing.model}\n"
                f"  API key  : {existing.api_key[:8]}...{existing.api_key[-4:]}\n\n"
                f"[dim]Run [bold]codedna setup --reset[/bold] to reconfigure.[/dim]\n"
                f"[dim]Run [bold]codedna setup --show[/bold] for details.[/dim]",
                border_style="yellow",
            )
        )
        return

    if existing and reset:
        console.print(f"  [yellow]![/yellow] Resetting existing configuration...")
        AIConfig.clear()
        console.print(f"  [green]✓[/green] Old config cleared")
        console.print()

    # ── Step 1: Provider ──────────────────────────────────────────────
    console.print("[bold]Step 1/4 — Choose AI provider[/bold]")
    for i, p in enumerate(PROVIDERS, 1):
        default_model = DEFAULT_MODELS.get(p, "?")
        console.print(f"  [cyan]{i}[/cyan]) {p}  [dim](default model: {default_model})[/dim]")
    console.print()

    while True:
        choice = typer.prompt("  Select provider (1-3)", default="1")
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(PROVIDERS):
                provider = PROVIDERS[idx]
                break
        except ValueError:
            pass
        console.print(f"  [red]✗[/red] Invalid choice '{choice}'. Try 1, 2, or 3.")

    console.print(f"  [green]✓[/green] Provider: [bold]{provider}[/bold]")
    console.print()

    # ── Step 2: API key ───────────────────────────────────────────────
    console.print("[bold]Step 2/4 — Enter API key[/bold]")
    env_var = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY", "minimax": "MINIMAX_API_KEY"}.get(provider, "API_KEY")
    console.print(f"  [dim]Tip: leave blank to use ${env_var} environment variable[/dim]")
    while True:
        api_key = typer.prompt(f"  {provider} API key", hide_input=True, default="")
        if api_key:
            break
        import os
        env_val = os.environ.get(env_var, "").strip()
        if env_val:
            api_key = env_val
            console.print(f"  [green]✓[/green] Using ${env_var} from environment")
            break
        console.print(f"  [red]✗[/red] API key is required. Press Ctrl+C to abort.")
    console.print()

    # ── Step 3: Model ──────────────────────────────────────────────────
    console.print("[bold]Step 3/4 — Choose model[/bold]")
    default_model = DEFAULT_MODELS.get(provider, "")
    model = typer.prompt(f"  Model", default=default_model)
    console.print(f"  [green]✓[/green] Model: [bold]{model}[/bold]")
    console.print()

    # ── Step 4: Enable + save ─────────────────────────────────────────
    console.print("[bold]Step 4/4 — Enable & save[/bold]")
    enabled = typer.confirm("  Enable AI analysis?", default=True)

    cfg = AIConfig(provider=provider, api_key=api_key, model=model, enabled=enabled)
    cfg.save()

    console.print()
    console.print(
        Panel(
            f"[bold green]✓ Configuration saved![/bold green]\n\n"
            f"  Provider : {provider}\n"
            f"  Model    : {model}\n"
            f"  Enabled  : {'yes' if enabled else 'no'}\n"
            f"  Location : {AI_CONFIG_PATH} [dim](chmod 600)[/dim]",
            border_style="green",
            padding=(1, 2),
        )
    )

    # ── Optional: test the connection ─────────────────────────────────
    if enabled and typer.confirm("\n  Run a quick connectivity test?", default=True):
        console.print(f"  [dim]Pinging {provider}...[/dim]")
        try:
            result = ai_analyze(command="ping", output="Reply with just the word 'pong' and nothing else.")
            console.print(f"  [green]✓[/green] Connection OK — response: [dim]{(result or '').strip()[:80]}[/dim]")
        except Exception as e:
            console.print(f"  [yellow]![/yellow] Connection test failed: {type(e).__name__}: {e}")
            console.print(f"  [dim]Your config is saved, but the API key may be invalid.[/dim]")

    console.print()
    console.print("[dim]Next steps:[/dim]")
    console.print("  • [cyan]codedna setup --show[/cyan]   view current config")
    console.print("  • [cyan]codedna setup --reset[/cyan]   reconfigure")
    console.print("  • [cyan]codedna scan[/cyan]            start analyzing your repo")
    console.print()


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
def _shorten_path(full_path: str, root: str) -> str:
    """Shorten long paths relative to repo root."""
    try:
        rel_path = Path(full_path).relative_to(Path(root))
        path_str = str(rel_path)
        if len(path_str) > 40:
            parts = Path(path_str).parts
            if len(parts) > 3:
                return f".../{'/'.join(parts[-2:])}"
        return path_str
    except ValueError:
        return full_path[-40:] if len(full_path) > 40 else full_path


def _risk_label(percentage: float) -> tuple[str, str]:
    """Return risk label and color based on AI percentage."""
    if percentage >= 70:
        return "HIGH", "red"
    elif percentage >= 40:
        return "MEDIUM", "yellow"
    else:
        return "LOW", "green"


def main() -> None:
    """CLI entry point."""
    app()


if __name__ == "__main__":
    main()
