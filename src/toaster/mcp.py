import time
from pathlib import Path
from fastmcp import FastMCP

from toaster.exceptions import ToasterError
from toaster.commands import init_async, inspect_async, skeleton_async, resolve_async

# Initialize the FastMCP server
mcp = FastMCP("Toaster")

@mcp.tool()
async def init(path: str = ".", use_cache: bool = True, write_skeleton: bool = True) -> str:
    """
    Parse files and setup the Toaster SQLite database for a project.
    Always run this first if the database does not exist.
    
    Args:
        path: Path to the project root directory to scan.
        use_cache: Load cache if it exists.
        write_skeleton: Build skeleton files if they don't exist.
    """
    try:
        start_time = time.perf_counter()
        target_path = Path(path).resolve()
        
        await init_async(target_path, use_cache, write_skeleton)
        
        elapsed = time.perf_counter() - start_time
        return f"✅ Success! Initialization saved in {elapsed:.4f} seconds."
    except ToasterError as e:
        return f"❌ Error: {e}"


@mcp.tool()
async def inspect(id: str, path: str = ".", include_body: bool = False) -> str:
    """
    Output the AST details and code for a specific struct ID.
    Use this when you need the full implementation details of a specific function or class.
    
    Args:
        id: The unique Toaster ID of the struct to inspect.
        path: Path to the project root directory.
        include_body: Include the raw code body in the output.
    """
    try:
        target_path = Path(path).resolve()
        result = await inspect_async(id, target_path, include_body)
        return str(result)
    except ToasterError as e:
        return f"❌ Error: {e}"


@mcp.tool()
async def skeleton(subpath: str, path: str = ".") -> str:
    """
    Output the .toast skeleton format for all files matching a specific subpath.
    Use this to understand the high-level architecture, classes, and function signatures of a file or directory without reading the full code.
    
    Args:
        subpath: File or directory path relative to the project root to generate a skeleton for.
        path: Path to the project root directory.
    """
    try:
        target_path = Path(path).resolve()
        result = await skeleton_async(subpath, target_path)
        return str(result)
    except ToasterError as e:
        return f"❌ Error: {e}"


@mcp.tool()
async def resolve(name: str, path: str = ".") -> str:
    """
    Find the exact ID of a struct by searching its name or identifier.
    Use this when you know the name of a method or class but need its ID for the 'inspect' tool.
    
    Args:
        name: Method or Class name to search for (partial matches allowed).
        path: Path to the project root directory.
    """
    try:
        target_path = Path(path).resolve()
        result = await resolve_async(name, target_path)
        return str(result)
    except ToasterError as e:
        return f"❌ Error: {e}"


if __name__ == "__main__":
    mcp.run()