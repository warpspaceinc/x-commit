"""Command-line interface for x-commit."""

import logging
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .analyzer import CommitAnalyzer
from .config import get_config
from .formatter import ConsoleFormatter

# Configure console with force_terminal and legacy_windows settings for better Windows compatibility
console = Console(force_terminal=True, legacy_windows=False)


def setup_logging(level: str = "INFO"):
    """Setup logging configuration."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )


@click.group()
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
    default="INFO",
    help="Set logging level",
)
def cli(log_level: str):
    """X-Commit: GitHub commit analyzer with Claude AI.

    Analyze GitHub commits and generate detailed reports using Claude AI.
    """
    setup_logging(log_level)


@cli.command()
@click.argument("commit")
@click.option(
    "-o",
    "--output",
    type=click.Path(path_type=Path),
    help="Output file path (default: auto-generated in reports/)",
)
@click.option(
    "--stdout",
    is_flag=True,
    help="Print report to stdout instead of saving to file",
)
@click.option(
    "-l",
    "--language",
    type=click.Choice(["korean", "english", "ko", "en"], case_sensitive=False),
    default="korean",
    help="Analysis language (default: korean)",
)
@click.option(
    "--repo",
    help="Repository in format 'owner/repo' (required if COMMIT is a SHA)",
)
def analyze(
    commit: str,
    output: Optional[Path],
    stdout: bool,
    language: str,
    repo: Optional[str],
):
    """Analyze a GitHub commit.

    COMMIT can be either:
    - A full GitHub commit URL (e.g., https://github.com/owner/repo/commit/abc123)
    - A commit SHA (requires --repo option)

    Examples:

      # Analyze by URL
      x-commit analyze https://github.com/torvalds/linux/commit/abc123

      # Analyze by SHA with custom output
      x-commit analyze abc123 --repo torvalds/linux -o my-report.md

      # Print to stdout instead of file
      x-commit analyze https://github.com/owner/repo/commit/abc123 --stdout

      # Analyze in English
      x-commit analyze https://github.com/owner/repo/commit/abc123 --language english
    """
    try:
        config = get_config()
    except ValueError as e:
        console.print(f"[red]{ConsoleFormatter.format_error(str(e))}[/red]")
        console.print("\n[yellow]Hint: Copy .env.example to .env and fill in your API keys.[/yellow]")
        sys.exit(1)

    # Normalize language
    lang = "english" if language.lower() in ["english", "en"] else "korean"

    # Determine if commit is a URL or SHA
    is_url = commit.startswith("http://") or commit.startswith("https://")

    if not is_url and not repo:
        # Check if default repo is configured
        if config.github_default_repo:
            repo = config.github_default_repo
            console.print(
                f"[yellow]{ConsoleFormatter.format_info(f'Using default repository: {repo}')}[/yellow]"
            )
        else:
            console.print(
                f"[red]{ConsoleFormatter.format_error('Repository required for SHA commits')}[/red]"
            )
            console.print(
                "\n[yellow]Use --repo option or set GITHUB_DEFAULT_REPO in .env[/yellow]"
            )
            sys.exit(1)

    # Initialize analyzer
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Create analyzer
        task = progress.add_task("Initializing...", total=None)
        analyzer = CommitAnalyzer()

        # Fetch and analyze commit
        try:
            progress.update(task, description="Fetching commit from GitHub...")

            if is_url:
                commit_info, file_changes = analyzer.github_client.get_commit_by_url(
                    commit
                )
            else:
                owner, repo_name = repo.split("/")
                commit_info, file_changes = analyzer.github_client.get_commit(
                    owner, repo_name, commit
                )

            console.print(
                f"\n[green]{ConsoleFormatter.format_success('Commit fetched successfully')}[/green]"
            )
            console.print(f"  Repository: {commit_info.repository}")
            console.print(f"  Commit: {commit_info.sha[:8]}")
            console.print(f"  Author: {commit_info.author_name}")
            console.print(
                f"  Changes: {commit_info.files_changed} files "
                f"(+{commit_info.additions} -{commit_info.deletions})"
            )

            progress.update(task, description="Analyzing with Claude AI...")
            analysis = analyzer._analyze_commit(commit_info, file_changes, lang)

            console.print(
                f"[green]{ConsoleFormatter.format_success('Analysis completed')}[/green]"
            )

            # Generate report
            progress.update(task, description="Generating report...")

            if stdout:
                # Print to stdout
                report = analyzer.generate_report(
                    commit_info, file_changes, analysis, None
                )
                console.print("\n" + "=" * 80)
                console.print(report)
                console.print("=" * 80)
            else:
                # Save to file
                if not output:
                    # Auto-generate filename
                    timestamp = commit_info.date.strftime("%Y%m%d_%H%M%S")
                    filename = f"{commit_info.repository.replace('/', '_')}_{commit_info.sha[:8]}_{timestamp}.md"
                    output = config.output_dir / filename

                report = analyzer.generate_report(
                    commit_info, file_changes, analysis, output
                )

                console.print(
                    f"\n[green]{ConsoleFormatter.format_success('Report saved successfully')}[/green]"
                )
                console.print(f"  Location: {output.absolute()}")

        except ValueError as e:
            progress.stop()
            console.print(f"\n[red]{ConsoleFormatter.format_error(str(e))}[/red]")
            sys.exit(1)
        except Exception as e:
            progress.stop()
            console.print(
                f"\n[red]{ConsoleFormatter.format_error(f'Analysis failed: {e}')}[/red]"
            )
            logging.exception("Analysis failed")
            sys.exit(1)


@cli.command()
def version():
    """Show version information."""
    from . import __version__
    console.print(f"x-commit version {__version__}")


@cli.command()
@click.argument("message")
@click.option(
    "--all",
    is_flag=True,
    help="Extract all commit references (not just the first one)",
)
def parse_message(message: str, all: bool):
    """Parse a Slack message and extract GitHub commit information.

    MESSAGE can be in various formats:
    - GitHub Slack app: "user pushed to branch: url - message"
    - Direct URL: https://github.com/owner/repo/commit/sha
    - Markdown link: [text](url)
    - Slack link: <url|text>

    Examples:

      # Parse GitHub Slack app format
      x-commit parse-message "rick pushed to main: https://github.com/owner/repo/commit/abc123 - Fix bug"

      # Parse direct URL
      x-commit parse-message "https://github.com/owner/repo/commit/abc123"

      # Parse Slack link format
      x-commit parse-message "Check this: <https://github.com/owner/repo/commit/abc123|View commit>"

      # Extract all commits from a message
      x-commit parse-message "See commits: url1 and url2" --all
    """
    from .message_parser import MessageParser

    parser = MessageParser()

    if all:
        # Extract all commits
        commits = parser.extract_all_commits(message)

        if not commits:
            console.print("[yellow]No GitHub commit URLs found in the message.[/yellow]")
            sys.exit(1)

        console.print(f"[green]Found {len(commits)} commit(s):[/green]\n")

        for i, commit in enumerate(commits, 1):
            console.print(f"[bold]Commit {i}:[/bold]")
            console.print(f"  Repository: {commit.owner}/{commit.repo}")
            console.print(f"  SHA: {commit.sha}")
            console.print(f"  URL: {commit.commit_url}")
            if commit.branch:
                console.print(f"  Branch: {commit.branch}")
            if commit.author:
                console.print(f"  Author: {commit.author}")
            if commit.message:
                console.print(f"  Message: {commit.message}")
            console.print()

    else:
        # Extract first commit
        commit = parser.parse_message(message)

        if not commit:
            console.print("[yellow]No GitHub commit URL found in the message.[/yellow]")
            console.print("\n[cyan]Supported formats:[/cyan]")
            console.print('  - "user pushed to branch: url - message"')
            console.print("  - https://github.com/owner/repo/commit/sha")
            console.print("  - [text](url)")
            console.print("  - <url|text>")
            sys.exit(1)

        console.print("[green]Successfully parsed commit information:[/green]\n")
        console.print(f"  Repository: [bold]{commit.owner}/{commit.repo}[/bold]")
        console.print(f"  SHA: [bold]{commit.sha}[/bold]")
        console.print(f"  URL: {commit.commit_url}")

        if commit.branch:
            console.print(f"  Branch: {commit.branch}")
        if commit.author:
            console.print(f"  Author: {commit.author}")
        if commit.message:
            console.print(f"  Message: {commit.message}")

        console.print(f"\n[cyan]You can analyze this commit with:[/cyan]")
        console.print(f"  x-commit analyze {commit.commit_url}")


@cli.command()
@click.option(
    "--mode",
    type=click.Choice(["socket", "http"], case_sensitive=False),
    default="socket",
    help="Server mode: socket (development) or http (production)",
)
@click.option(
    "--port",
    type=int,
    default=3000,
    help="Port for HTTP mode (default: 3000)",
)
def serve(mode: str, port: int):
    """Start the Slack bot server.

    The bot will listen for GitHub commit messages in Slack and automatically
    analyze them using Claude AI.

    Modes:
      - socket: Socket Mode for development (requires SLACK_APP_TOKEN)
      - http: HTTP Mode for production (requires public HTTPS endpoint)

    Examples:

      # Start in Socket Mode (development)
      x-commit serve --mode socket

      # Start HTTP server for production
      x-commit serve --mode http --port 3000
    """
    try:
        config = get_config()
    except ValueError as e:
        console.print(f"[red]{ConsoleFormatter.format_error(str(e))}[/red]")
        sys.exit(1)

    # Check Slack configuration
    if not config.slack_bot_token:
        console.print(
            "[red][ERROR] SLACK_BOT_TOKEN is required. "
            "Please install the app to your workspace and add the token to .env[/red]"
        )
        sys.exit(1)

    if not config.slack_signing_secret:
        console.print(
            "[red][ERROR] SLACK_SIGNING_SECRET is required. "
            "Please add it to .env[/red]"
        )
        sys.exit(1)

    console.print("[bold]Starting X-Commit Slack Bot...[/bold]\n")
    console.print(f"  Mode: {mode}")

    # Show analysis mode
    if config.slack_auto_analyze:
        console.print("  Analysis mode: [bold green]AUTO[/bold green] - Analyzes all GitHub commits automatically")
    else:
        console.print("  Analysis mode: [bold yellow]MENTION[/bold yellow] - Only analyzes when @x-commit is mentioned")

    if config.slack_channel:
        console.print(f"  Monitoring channel: {config.slack_channel}")
    else:
        console.print("  Monitoring: All channels (no filter)")

    if config.slack_target_branches:
        console.print(f"  Target branches: [bold cyan]{', '.join(config.slack_target_branches)}[/bold cyan]")
    else:
        console.print("  Target branches: All branches")

    try:
        from .bot import create_bot

        bot = create_bot()

        if mode.lower() == "socket":
            # Socket Mode
            if not config.slack_app_token:
                console.print(
                    "\n[red][ERROR] SLACK_APP_TOKEN is required for Socket Mode.[/red]"
                )
                console.print(
                    "[yellow]Enable Socket Mode in Slack app settings and add the token to .env[/yellow]"
                )
                sys.exit(1)

            console.print("\n[green]Bot is running in Socket Mode![/green]")
            console.print("Press Ctrl+C to stop.\n")
            bot.start_socket_mode()

        else:
            # HTTP Mode
            console.print(f"\n[green]Starting HTTP server on port {port}...[/green]")
            console.print(f"[yellow]Make sure your Request URL in Slack is set to:")
            console.print(f"  https://your-domain.com/slack/events[/yellow]\n")

            from flask import Flask, request
            from slack_bolt.adapter.flask import SlackRequestHandler

            flask_app = Flask(__name__)
            handler = SlackRequestHandler(bot.get_app())

            @flask_app.route("/slack/events", methods=["POST"])
            def slack_events():
                return handler.handle(request)

            @flask_app.route("/health", methods=["GET"])
            def health():
                return {"status": "ok"}, 200

            console.print("[green]Bot is running![/green]")
            console.print("Press Ctrl+C to stop.\n")

            flask_app.run(host="0.0.0.0", port=port)

    except KeyboardInterrupt:
        console.print("\n[yellow]Bot stopped by user.[/yellow]")
    except Exception as e:
        console.print(f"\n[red][ERROR] Failed to start bot: {e}[/red]")
        logging.exception("Bot startup failed")
        sys.exit(1)


@cli.command()
def config_check():
    """Check configuration and verify API credentials."""
    console.print("[bold]Checking configuration...[/bold]\n")

    try:
        config = get_config()
        console.print("[green][OK] Configuration loaded successfully[/green]")

        # Check GitHub token
        console.print("\n[bold]GitHub API:[/bold]")
        console.print(f"  Token: {'[OK]' if config.github_token else '[X]'} {'Set' if config.github_token else 'Not set'}")
        if config.github_default_repo:
            console.print(f"  Default repo: {config.github_default_repo}")

        # Check Claude API
        console.print("\n[bold]Claude API:[/bold]")
        console.print(f"  API Key: {'[OK]' if config.anthropic_api_key else '[X]'} {'Set' if config.anthropic_api_key else 'Not set'}")
        console.print(f"  Model: {config.claude_model}")

        # Check output directory
        console.print("\n[bold]Application:[/bold]")
        console.print(f"  Output directory: {config.output_dir}")
        console.print(f"  Log level: {config.log_level}")
        console.print(f"  Max diff lines: {config.max_diff_lines}")

        # Test API connections
        console.print("\n[bold]Testing API connections...[/bold]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Testing GitHub API...", total=None)

            try:
                from .github_client import GitHubClient

                github_client = GitHubClient()
                user = github_client.client.get_user()
                console.print(f"[green]  [OK] GitHub API: Connected as {user.login}[/green]")
            except Exception as e:
                console.print(f"[red]  [X] GitHub API: Failed - {e}[/red]")

            progress.update(task, description="Testing Claude API...")

            try:
                from .claude_client import ClaudeClient

                claude_client = ClaudeClient()
                # Just check if client initializes
                console.print(f"[green]  [OK] Claude API: Initialized[/green]")
            except Exception as e:
                console.print(f"[red]  [X] Claude API: Failed - {e}[/red]")

        console.print("\n[green]Configuration check complete![/green]")

    except ValueError as e:
        console.print(f"[red][ERROR] Configuration error: {e}[/red]")
        console.print("\n[yellow]Hint: Copy .env.example to .env and fill in your API keys.[/yellow]")
        sys.exit(1)


def main():
    """Main entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
