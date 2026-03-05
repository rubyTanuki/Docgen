import asyncio
import os
import time
import json
from pathlib import Path
import typer
from typing import Annotated

from toaster.llm import GeminiClient
from toaster.core import MemberRegistry, toast, Verbosity
from toaster.languages.java import JavaParser

# Initialize the Typer app
app = typer.Typer(
    name="toaster",
    help="AST scraper for LLM RAG context generation.",
    add_completion=False # Optional: Turns off the auto-generated completion install command for cleaner help menus
)

async def _init_ast_async(target_path: Path, use_cache: bool = True) -> BaseParser:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if GEMINI_API_KEY is None:
        print("❌ Error: API key not found. Set the GEMINI_API_KEY environment variable.")
        raise typer.Exit(code=1)
    
    # Dependency Injection
    llm = GeminiClient(api_key=GEMINI_API_KEY) 
    registry = MemberRegistry()
    
    print(f"🔍 Parsing files in '{target_path}' and linking AST...")
    parser = JavaParser(target_path, llm, registry)
    await parser.parse(use_cache=use_cache)
    
    return parser

async def _run_init_async(target_path: Path, use_cache: bool = True, skeleton: bool = True):
    """Core asynchronous logic for scraping and parsing."""
    start_time = time.perf_counter()
    
    parser = await _init_ast_async(target_path, use_cache=use_cache)
    
    # Write Skeleton
    if skeleton:
        parser.write_skeleton()
        
    # Write Cache
    parser.write_cache()
        
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time

    print(f"✅ Success! Initialization saved in {elapsed_time:.4f} seconds.")


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
    skeleton: Annotated[
        bool, 
        typer.Option(
            "--skeleton/--no-skeleton", 
            help="Build skeleton if it doesn't exist"
            )
    ] = True
):
    """Parse files and generate RAG context."""
    # Wrap the async call in asyncio.run
    asyncio.run(_run_init_async(path, use_cache, skeleton))


async def _inspect_async(id:str, target_path: Path, include_body: bool = False):
    parser = await _init_ast_async(target_path, use_cache=True)
    
    struct = parser.registry.get_struct_by_id(id=id)
    if struct is None:
        print(f"❌ Error: Struct not found with id {id}.")
        raise typer.Exit(code=1)
    
    if include_body:
        print(toast.dumps(struct, verbosity=Verbosity.FULL))
    else:
        print(toast.dumps(struct, verbosity=Verbosity.VERBOSE))
    

# You can easily add more commands here later!
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
        ] = False
):
    if not (path / ".toaster_cache.json").exists():
        print("❌ Error: Cache not found. Run 'toaster init' first.")
        raise typer.Exit(code=1)
    # Wrap the async call in asyncio.run
    asyncio.run(_inspect_async(id, path, include_body))


if __name__ == "__main__":
    app()