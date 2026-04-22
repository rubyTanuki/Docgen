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
    registry = Registry(use_cache=use_cache, db=db, project_path=target_path)
    logger.info("Building AST...")
    
    parser = BaseParser(target_path, llm, registry)
    logger.info("Parsing files...")
    await parser.parse()
    logger.success("✅ Parsed files")
    return parser

async def init_async(target_path: Path, use_cache: bool = True):
    """Core asynchronous logic for scraping and parsing."""
    
    # Parse and resolve AST
    parser = await _build_ast_async(target_path, use_cache=use_cache)
        
    # Write Cache
    parser.registry.save_to_cache()
    
async def inspect_async(struct_id:str, project_path: Path, include_body: bool = False, pretty: bool = True):
    _verify_db_exists(project_path)
    
    db = SQLiteCache(project_path / ".toaster" / "cache.db")
    
    registry = Registry(db=db, use_cache=True, project_path=project_path)
    struct_obj = registry.get_struct_by_id(struct_id)
    if struct_obj is None:
        raise StructNotFoundError(f"Struct not found with id {struct_id}.")
    
    logger.debug(f"{struct_obj.uid}'s children: {[str(child) for child in struct_obj.all_children]}")
    
    
    return toast.dump(struct_obj, verbosity=Verbosity.VERBOSE, include_body=include_body, pretty=pretty)
    
async def skeleton_async(subpath: str, project_path: Path, pretty: bool = True):
    _verify_db_exists(project_path)
    
    db = SQLiteCache(project_path / ".toaster" / "cache.db")
    registry = Registry(db=db, project_path=project_path)
    
    relative_subpath = Path(subpath).resolve().relative_to(project_path.resolve())
    logger.debug(f"Loading subtree for relative path: {relative_subpath}")
    
    registry.load_filepath(relative_subpath)
    if not registry.files:
        raise FileNotFoundError(f"No files found matching path '{subpath}'.")
    
    return toast.dump_skeleton(registry.root, pretty=pretty)

active_tasks = {}

async def watch_async(target_path: Path):
    llm = get_llm_client()
    
    logger.info("Starting Listener")
    try:
        async for changes in awatch(target_path):
            for change_type, path in changes:
                path = Path(path).relative_to(target_path)
                if ".toaster" in str(path):
                    continue
                
                existing_task = active_tasks.get(path)
                if existing_task and not existing_task.done():
                    existing_task.cancel()
                
                match change_type:
                    case Change.modified:
                        logger.info(f"File modified: {path}")
                    case Change.added:
                        logger.info(f"File added: {path}")
                    case Change.deleted:
                        logger.info(f"File deleted: {path}")
                        # TODO: handle deletions in the db
                        
                new_task = asyncio.create_task(
                    process_single_file(target_path, path, llm)
                )
                active_tasks[path] = new_task
                
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("\n🛑 Stopping listener...")

async def process_single_file(project_dir: Path, filepath: Path, llm_client: GeminiClient):
    logger.info(f"Processing file {filepath}")
    try:
        db = SQLiteCache(project_dir / ".toaster" / "cache.db")
        
        registry = Registry(db=db, use_cache=True, project_path=project_dir)
        parser = BaseParser(filepath, llm_client, registry)
        
        parser.parse_path(filepath)
        
        parser.resolve_dependencies()
        
        await asyncio.to_thread(registry.save_to_cache, stale=True)
        logger.debug("Wrote Cache w/ stale descriptions")
        
        # resolve the descriptions and do the second cache write
        await parser.resolve_descriptions_async()
        await asyncio.to_thread(registry.save_to_cache)
        logger.debug("Wrote Cache w/ resolved descriptions")
        
        logger.success(f"✅ Processed file {filepath}")
        
    except asyncio.CancelledError:
        logger.warning(f"Task cancelled on {filepath}")
    except Exception as e:
        logger.warning(f"Error processing file {filepath}: {e}")
    finally:
        if active_tasks.get(filepath) == asyncio.current_task():
            del active_tasks[filepath]