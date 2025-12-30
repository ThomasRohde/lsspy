"""CLI interface for LSSPY."""

import sys
import webbrowser
from pathlib import Path

import typer
import uvicorn
from rich.console import Console

from lsspy import __version__
from lsspy.server import create_app, set_lodestar_dir

app = typer.Typer(
    help="LSSPY - Lodestar Visualizer Dashboard",
    no_args_is_help=False,
    add_completion=False,
)
console = Console()


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"lsspy version {__version__}")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def start(
    ctx: typer.Context,
    path: str = typer.Argument(
        None,
        help="Path to the .lodestar directory or parent directory (auto-detects .lodestar)",
    ),
    port: int = typer.Option(8000, "--port", "-p", help="Port to run the web server on"),
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host address to bind to"),
    no_open: bool = typer.Option(False, "--no-open", help="Don't automatically open browser"),
    poll_interval: int = typer.Option(
        1,
        "--poll-interval",
        help="File polling interval in seconds (if file watching fails)",
    ),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging"),
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
) -> None:
    """Start the LSSPY dashboard server.

    If no path is provided, auto-detects .lodestar in the current directory.
    """
    # Skip if version flag was handled
    if ctx.resilient_parsing:
        return

    # Auto-detect .lodestar directory
    if path is None:
        lodestar_path = Path.cwd() / ".lodestar"
        if not lodestar_path.exists():
            console.print("[red]Error: .lodestar directory not found in current directory[/red]")
            console.print("Please specify the path to .lodestar directory")
            raise typer.Exit(1)
    else:
        lodestar_path = Path(path)
        # If path points to parent directory, look for .lodestar inside
        if not lodestar_path.name == ".lodestar":
            lodestar_path = lodestar_path / ".lodestar"

    # Validate .lodestar directory
    if not lodestar_path.exists():
        console.print(f"[red]Error: Directory not found: {lodestar_path}[/red]")
        raise typer.Exit(1)

    if not lodestar_path.is_dir():
        console.print(f"[red]Error: Not a directory: {lodestar_path}[/red]")
        raise typer.Exit(1)

    runtime_db = lodestar_path / "runtime.sqlite"
    spec_file = lodestar_path / "spec.yaml"

    if not runtime_db.exists():
        console.print(f"[yellow]Warning: runtime.sqlite not found at {runtime_db}[/yellow]")

    if not spec_file.exists():
        console.print(f"[yellow]Warning: spec.yaml not found at {spec_file}[/yellow]")

    # Display startup info
    if debug:
        console.print("[bold cyan]Debug mode enabled[/bold cyan]")

    console.print("[bold green]Starting LSSPY dashboard...[/bold green]")
    console.print(f"Monitoring: {lodestar_path.absolute()}")
    console.print(f"Server: http://{host}:{port}")
    console.print(f"Poll interval: {poll_interval}s")

    # Open browser if requested
    if not no_open:
        console.print("[dim]Opening browser...[/dim]")
        # Open browser after a short delay to allow server to start
        import threading

        def open_browser() -> None:
            import time

            time.sleep(1.5)
            webbrowser.open(f"http://{host}:{port}")

        threading.Thread(target=open_browser, daemon=True).start()

    # Configure and start server
    set_lodestar_dir(lodestar_path)
    app = create_app()

    # Start uvicorn server
    log_level = "debug" if debug else "info"
    try:
        uvicorn.run(app, host=host, port=port, log_level=log_level, access_log=debug)
    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped[/yellow]")
        raise typer.Exit(0)


def main() -> None:
    """Main entry point."""
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(0)


if __name__ == "__main__":
    main()
