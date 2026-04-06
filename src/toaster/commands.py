import asyncio
import os
import shutil
import time
import json
from pathlib import Path
from typing import Annotated
from watchfiles import awatch, Change
from loguru import logger

from toaster.llm import GeminiClient
from toaster.core import Registry, toast, Verbosity, BaseParser, SQLiteCache

from toaster.exceptions import APIKeyError, StructNotFoundError, ResolveError, DatabaseNotFoundError, TargetFileNotFoundError

def _verify_db_exists(target_path: Path):
    if not os.path.exists(target_path):
        raise DatabaseNotFoundError("Database not found. Run 'toaster init' first.")

def get_llm_client():
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if GEMINI_API_KEY is None:
        raise APIKeyError("API key not found.")
    
    return GeminiClient(api_key=GEMINI_API_KEY)

def clean_db(target_path: Path):
    if os.path.exists(target_path / ".toaster"):
        shutil.rmtree(target_path / ".toaster")
        logger.info("Database cleaned.")
    else:
        logger.warning("No database found to clean.")

async def _build_ast_async(target_path: Path, use_cache: bool = True) -> BaseParser:
    llm = get_llm_client()
    db = SQLiteCache(target_path / ".toaster" / "cache.db")
    registry = Registry(use_cache=use_cache, db=db)
    logger.info("Building AST...")
    
    parser = BaseParser(target_path, llm, registry)
    logger.info("Parsing files...")
    await parser.parse()
    logger.success("✅ Parsed files")
    return parser

async def init_async(target_path: Path, use_cache: bool = True, write_skeleton: bool = False):
    """Core asynchronous logic for scraping and parsing."""
    
    parser = await _build_ast_async(target_path, use_cache=use_cache)
    
    
    # Write Skeleton
    # if write_skeleton:
    #     parser.write_skeleton()
        
    # Write Cache
    parser.write_cache()
    
async def inspect_async(id:str, target_path: Path, include_body: bool = False, pretty: bool = True):
    _verify_db_exists(target_path)
    
    registry = MemberRegistry(str(target_path))
    struct_obj = registry.get_struct_from_db(id)
    if struct_obj is None:
        raise StructNotFoundError(f"Struct not found with id {id}.")
    
    return toast.dumps(struct_obj, verbosity=Verbosity.VERBOSE, include_body=include_body, pretty=pretty)
    
async def skeleton_async(subpath: str, target_path: Path):
    _verify_db_exists(target_path)
    
    registry = MemberRegistry(str(target_path))
    files = registry.get_files_by_path(subpath)
    if not files:
        raise FileNotFoundError(f"No files found matching path '{subpath}'.")
    
    return toast.dump_files(files, verbosity=Verbosity.SKELETON, pretty=False)
    
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
        # logger.trace(toast.dump_parser(parser))
        parser.load_cache()
        # TODO: mark the descriptions as stale here
        await asyncio.to_thread(parser.write_cache)
        logger.debug("✅ Wrote Cache #1")
        
        # now resolve the descriptions and do the second cache write
        logger.debug("Resolving Descriptions...")
        await parser.resolve_descriptions()
        await asyncio.to_thread(parser.write_cache)
        logger.debug("✅ Wrote Cache #2")
        # logger.trace(toast.dump_parser(parser))
    except asyncio.CancelledError:
        logger.warning(f"Task cancelled on {filepath}")
    except Exception as e:
        logger.warning(f"Error processing file {filepath}: {e}")
    finally:
        if active_tasks.get(filepath) == asyncio.current_task():
            del active_tasks[filepath]