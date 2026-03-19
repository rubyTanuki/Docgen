import asyncio
import os
import time
import json
from pathlib import Path
from typing import Annotated

from toaster.llm import GeminiClient
from toaster.core import MemberRegistry, toast, Verbosity, ParserProvider

from toaster.exceptions import APIKeyError, StructNotFoundError, ResolveError

async def _build_ast_async(target_path: Path, use_cache: bool = True) -> BaseParser:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if GEMINI_API_KEY is None:
        raise APIKeyError("API key not found.")
    
    # Dependency Injection
    llm = GeminiClient(api_key=GEMINI_API_KEY) 
    registry = MemberRegistry(str(target_path))
    
    parser = ParserProvider.get_parser(target_path, llm, registry)
    await parser.parse(use_cache=use_cache)
    
    return parser

async def _init_async(target_path: Path, use_cache: bool = True, write_skeleton: bool = True):
    """Core asynchronous logic for scraping and parsing."""
    
    parser = await _build_ast_async(target_path, use_cache=use_cache)
    
    # Write Skeleton
    if write_skeleton:
        parser.write_skeleton()
        
    # Write Cache
    parser.write_cache()
    
async def _inspect_async(id:str, target_path: Path, include_body: bool = False):
    registry = MemberRegistry(str(target_path))
    struct_obj = registry.get_struct_from_db(id)
    if struct_obj is None:
        raise StructNotFoundError(f"Struct not found with id {id}.")
    
    verb = Verbosity.FULL if include_body else Verbosity.VERBOSE
    return toast.dumps(struct_obj, verbosity=verb)
    
async def _skeleton_async(subpath: str, target_path: Path):
    registry = MemberRegistry(str(target_path))
    files = registry.get_files_by_path(subpath)
    if not files:
        raise FileNotFoundError(f"No files found matching path '{subpath}'.")
    
    return toast.dump_files(files, verbosity=Verbosity.SKELETON)
    
async def _resolve_async(name: str, target_path: Path):
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