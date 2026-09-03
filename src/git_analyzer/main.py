import subprocess
from collections import Counter
from pathlib import Path

import typer
from rich.panel import Panel
from rich.console import Console
from rich.table import Table


app = typer.Typer(no_args_is_help=True)
console = Console()


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True, stderr=subprocess.DEVNULL).strip()


def top_changed_files(repo: Path, limit: int) -> list[tuple[str, int]]:
    output = git(repo, "log", "--name-only", "--pretty=format:")
    files = [line.strip() for line in output.splitlines() if line.strip()]
    return Counter(files).most_common(limit)


def commits_by_day(repo: Path, limit: int) -> list[tuple[str, int]]:
    output = git(repo, "log", "--date=short", "--pretty=format:%ad")
    days = [line.strip() for line in output.splitlines() if line.strip()]
    return Counter(days).most_common(limit)


def recent_commits(repo: Path, limit: int) -> list[list[str]]:
    output = git(repo, "log", f"-{limit}", "--date=short", "--pretty=format:%h|%ad|%an|%s")
    return [line.split("|", maxsplit=3) for line in output.splitlines() if line.strip()]


@app.command()
def analyze(
    repo: Path = typer.Option(Path("."), "--repo", "-r", help="Git repository to analyze."),
    limit: int = typer.Option(10, "--limit", "-n", help="Rows to show in ranking tables."),
) -> None:
    try:
        commits = git(repo, "rev-list", "--count", "HEAD")
        authors = git(repo, "shortlog", "-sn", "HEAD")
        branch = git(repo, "rev-parse", "--abbrev-ref", "HEAD")
        last_commit = git(repo, "log", "-1", "--date=short", "--pretty=format:%h %ad %an - %s")
        files = top_changed_files(repo, limit)
        busy_days = commits_by_day(repo, limit)
        recent = recent_commits(repo, 5)
    except Exception:
        console.print(f"[red]Not a Git repository:[/red] {repo}")
        raise typer.Exit(code=1)

    console.print(
        Panel.fit(
            f"Repository: [bold]{repo}[/bold]\n"
            f"Branch: [bold]{branch}[/bold]\n"
            f"Commits: [bold]{commits}[/bold]\n"
            f"Last commit: {last_commit}",
            title="Git Summary",
        )
    )

    table = Table(title="Git Summary")
    table.add_column("Metric")
    table.add_column("Value")
    table.add_row("Commits", commits)
    table.add_row("Authors", authors or "-")
    console.print(table)

    files_table = Table(title="Most Changed Files")
    files_table.add_column("File")
    files_table.add_column("Changes", justify="right")
    for file_name, count in files:
        files_table.add_row(file_name, str(count))
    console.print(files_table)

    days_table = Table(title="Busiest Commit Days")
    days_table.add_column("Date")
    days_table.add_column("Commits", justify="right")
    for day, count in busy_days:
        days_table.add_row(day, str(count))
    console.print(days_table)

    recent_table = Table(title="Recent Commits")
    recent_table.add_column("Hash")
    recent_table.add_column("Date")
    recent_table.add_column("Author")
    recent_table.add_column("Message")
    for row in recent:
        if len(row) == 4:
            recent_table.add_row(*row)
    console.print(recent_table)
