import asyncio
import os
import time
import json
from pathlib import Path
import typer
from typing import Annotated
from loguru import logger
from threading import Thread

from toaster.llm import GeminiClient
from toaster.core import Registry, toast, Verbosity
from toaster.exceptions import ToasterError

from toaster.commands import init_async, inspect_async, skeleton_async, watch_async, clean_db

from toaster.mcp import mcp

from toaster.core.logger import configure_cli_logging


# Initialize the Typer app
app = typer.Typer(
    name="toaster",
    help="AST scraper for LLM RAG context generation.",
    add_completion=False # Optional: Turns off the auto-generated completion install command for cleaner help menus
)

def _run_watcher_thread(target_path: Path):
    """
    Sets up an isolated async environment for the background thread.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        logger.info(f"Background watcher started on {target_path}")
        loop.run_until_complete(watch_async(target_path))
    except Exception as e:
        logger.exception(f"Fatal error in background watcher: {e}")
    finally:
        loop.close()
        logger.info("Background watcher shut down.")

@app.command("start-mcp")
def start_mcp():
    """Start the bare MCP server. Awaits agent initialization."""
    mcp.run()

@app.command()
def watch(
    path: Path = typer.Argument(
        ".", 
        help="Path to the project directory to scan",
        exists=True,       # Typer automatically checks if the path exists
        file_okay=False,   # Typer blocks files, only allowing directories
        dir_okay=True,
        resolve_path=True  # Converts relative paths to absolute paths automatically
    ),
    debug: Annotated[
        bool, 
        typer.Option(
            "--debug/--no-debug", 
            "-d/-nd",
            help="Enable debug logging"
            )
    ] = False
):
    """Watch for changes to files and update the SQLite database."""
    configure_cli_logging(debug)
    try:
        asyncio.run(watch_async(path))
    except ToasterError as e:
        typer.secho(f"❌ Error: {e}", fg="red", err=True)
        raise typer.Exit(code=1)

@app.command()
def clean(
    path: Path = typer.Argument(
        ".", 
        help="Path to the project directory to scan",
        exists=True,       # Typer automatically checks if the path exists
        file_okay=False,   # Typer blocks files, only allowing directories
        dir_okay=True,
        resolve_path=True  # Converts relative paths to absolute paths automatically
    ),
    debug: Annotated[
        bool, 
        typer.Option(
            "--debug/--no-debug", 
            "-d/-nd",
            help="Enable debug logging"
            )
    ] = False
):
    """Clean the SQLite database."""
    configure_cli_logging(debug)
    try:
        clean_db(path)
    except ToasterError as e:
        typer.secho(f"❌ Error: {e}", fg="red", err=True)
        raise typer.Exit(code=1)

@app.command()
def init(
    path: Path = typer.Argument(
        ".", 
        help="Path to the project directory to scan",
        exists=True,       # Typer automatically checks if the path exists
        file_okay=False,   # Typer blocks files, only allowing directories
        dir_okay=True,
        resolve_path=True  # Converts relative paths to absolute paths automatically
    ),
    use_cache: Annotated[
        bool, 
        typer.Option(
            "--use-cache/--no-cache", 
            help="Load cache if it exists"
            )
        ] = True,
    write_skeleton: Annotated[
        bool, 
        typer.Option(
            "--skeleton/--no-skeleton", 
            help="Build skeleton if it doesn't exist"
            )
    ] = True,
    debug: Annotated[
        bool, 
        typer.Option(
            "--debug/--no-debug", 
            "-d/-nd",
            help="Enable debug logging"
            )
    ] = False
):
    """Parse files and setup SQLite database."""
    configure_cli_logging(debug)
    start_time = time.perf_counter()
    try:
        asyncio.run(init_async(path, use_cache, write_skeleton))
    except ToasterError as e:
        typer.secho(f"❌ Error: {e}", fg="red", err=True)
        raise typer.Exit(code=1)
    
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time
    logger.debug(f"Finished in {elapsed_time:.4f} seconds.")


@app.command()
def inspect(
    id: Annotated[
        str, 
        typer.Argument()
    ],
    path: Path = typer.Argument(
        ".", 
        help="Path to the project directory to scan",
        exists=True,       # Typer automatically checks if the path exists
        file_okay=False,   # Typer blocks files, only allowing directories
        dir_okay=True,
        resolve_path=True  # Converts relative paths to absolute paths automatically
    ),
    include_body: Annotated[
        bool, 
        typer.Option(
            "--body/--no-body", 
            help="Include code body in output"
            )
        ] = False,
    pretty: Annotated[
        bool,
        typer.Option(
            "--pretty/--raw",
            help="Pretty format output with line wrapping and indentation (disable for raw output)"
        )
    ] = True,
    debug: Annotated[
        bool, 
        typer.Option(
            "--debug/--no-debug", 
            "-d/-nd",
            help="Enable debug logging"
            )
    ] = False
):
    """Output the AST details for a specific struct ID."""
    configure_cli_logging(debug)
    
    start_time = time.perf_counter()
    try:
        result = asyncio.run(inspect_async(id, path, include_body=include_body, pretty=pretty))
        print(result)
    except ToasterError as e:
        typer.secho(f"❌ Error: {e}", fg="red", err=True)
        raise typer.Exit(code=1)
    
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time
    logger.debug(f"Finished in {elapsed_time:.4f} seconds.")


@app.command()
def skeleton(
    subpath: Annotated[
        str, 
        typer.Argument(help="File or directory path relative to the project root to generate a skeleton for")
    ] = ".",
    path: Path = typer.Argument(
        ".", 
        help="Path to the project directory to scan",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True
    ),
    debug: Annotated[
        bool, 
        typer.Option(
            "--debug/--no-debug", 
            "-d/-nd",
            help="Enable debug logging"
            )
    ] = False
):
    """Output the .toast skeleton format for all files matching a specific subpath."""
    configure_cli_logging(debug)
    
    start_time = time.perf_counter()
    try:
        result = asyncio.run(skeleton_async(subpath, path))
        print(result)
    except ToasterError as e:
        typer.secho(f"❌ Error: {e}", fg="red", err=True)
        raise typer.Exit(code=1)
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time
    logger.debug(f"Finished in {elapsed_time:.4f} seconds.")

if __name__ == "__main__":
    app()