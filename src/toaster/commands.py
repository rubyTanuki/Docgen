import asyncio
import os
import time
import json
from pathlib import Path
from typing import Annotated
from watchfiles import awatch, Change
from loguru import logger

from toaster.llm import GeminiClient
from toaster.core import MemberRegistry, toast, Verbosity, ParserProvider

from toaster.exceptions import APIKeyError, StructNotFoundError, ResolveError, DatabaseNotFoundError, TargetFileNotFoundError

def _verify_db_exists(target_path: Path):
    if not os.path.exists(target_path):
        raise DatabaseNotFoundError("Database not found. Run 'toaster init' first.")

def get_llm_client():
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if GEMINI_API_KEY is None:
        raise APIKeyError("API key not found.")
    
    return GeminiClient(api_key=GEMINI_API_KEY)

async def _build_ast_async(target_path: Path, use_cache: bool = True) -> BaseParser:
    llm = get_llm_client()
    registry = MemberRegistry(str(target_path))
    
    parser = ParserProvider.get_parser(target_path, llm, registry)
    await parser.parse(use_cache=use_cache)
    
    return parser

async def init_async(target_path: Path, use_cache: bool = True, write_skeleton: bool = False):
    """Core asynchronous logic for scraping and parsing."""
    
    parser = await _build_ast_async(target_path, use_cache=use_cache)
    
    # Write Skeleton
    if write_skeleton:
        parser.write_skeleton()
        
    # Write Cache
    parser.write_cache()
    
async def inspect_async(id:str, target_path: Path, include_body: bool = False):
    _verify_db_exists(target_path)
    
    registry = MemberRegistry(str(target_path))
    struct_obj = registry.get_struct_from_db(id)
    if struct_obj is None:
        raise StructNotFoundError(f"Struct not found with id {id}.")
    
    verb = Verbosity.FULL if include_body else Verbosity.VERBOSE
    return toast.dumps(struct_obj, verbosity=verb)
    
async def skeleton_async(subpath: str, target_path: Path):
    _verify_db_exists(target_path)
    
    registry = MemberRegistry(str(target_path))
    files = registry.get_files_by_path(subpath)
    if not files:
        raise FileNotFoundError(f"No files found matching path '{subpath}'.")
    
    return toast.dump_files(files, verbosity=Verbosity.SKELETON)
    
async def resolve_async(name: str, target_path: Path):
    _verify_db_exists(target_path)
    
    registry = MemberRegistry(str(target_path))
    results = registry.resolve_name(name)
    
    if not results:
        raise ResolveError(f"No results found for '{name}'.")
    
    result_list = []
    for res in results:
        result_list.append(f"[{res['type']}] {res['id']} | {res['signature']}")
        if res.get('description'):
            result_list.append(res['description'])
    
    return '\n'.join(result_list)

active_tasks: dict[Path, asyncio.Task] = {}

async def watch_async(target_path: Path):
    llm = get_llm_client()
    
    logger.info("Starting Listener")
    try:
        async for changes in awatch(target_path):
            for change_type, path in changes:
                path = Path(path)
                if ".toaster" in str(path):
                    continue
                
                existing_task = active_tasks.get(path)
                if existing_task and not existing_task.done():
                    existing_task.cancel()
                
                match change_type:
                    case Change.modified:
                        logger.info(f"File modified: {path}")
                        
                        new_task = asyncio.create_task(
                            process_single_file(target_path, path, llm)
                        )
                        active_tasks[path] = new_task
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("\n🛑 Stopping listener...")

async def process_single_file(project_dir: Path, filepath: Path, llm_client: GeminiClient):
    logger.info(f"Processing file {filepath}")
    try:
        registry = MemberRegistry(str(project_dir))
        parser = ParserProvider.get_parser(project_dir, llm_client, registry)
        await parser.parse_path(filepath)
        parser.resolve_dependencies()
        logger.debug("✅ Resolved Dependencies")
        logger.trace(toast.dump_project(parser))
        parser.load_cache()
        # mark the descriptions as stale here
        await asyncio.to_thread(parser.write_cache)
        logger.debug("✅ Wrote Cache #1")
        
        # now resolve the descriptions and do the second cache write
        logger.debug("Resolving Descriptions...")
        await parser.resolve_descriptions()
        await asyncio.to_thread(parser.write_cache)
        logger.debug("✅ Wrote Cache #2")
        logger.trace(toast.dump_project(parser))
    except asyncio.CancelledError:
        logger.warning(f"Task cancelled on {filepath}")
        pass
    except Exception as e:
        logger.warning(f"Error processing file {filepath}: {e}")
    finally:
        if active_tasks.get(filepath) == asyncio.current_task():
            del active_tasks[filepath]