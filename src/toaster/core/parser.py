from pathlib import Path
from abc import ABC, abstractmethod
from collections import defaultdict
import asyncio
import json
import time

from toaster.core.models import BaseFile
from toaster.core.registry import MemberRegistry
from toaster.core.serializer import toast, Verbosity

class BaseParser(ABC):
    def __init__(self, project_dir: str, llm=None, registry: MemberRegistry=None):
        self.llm = llm
        self.registry = registry
        self.files: list[BaseFile] = []
        self.project_dir = project_dir
        self.path = Path(self.project_dir)
    async def parse(self, use_cache=True, subpath=None):
        # print(f"🔍 Parsing files in '{self.project_dir}' and linking AST...")
        
        # start_time = time.time()
        
        # t_parse = time.time()
        
        await self.parse_relative_path(subpath)
        # print(f"✅ Parsed Project Files in {time.time() - t_parse:.2f} seconds")
        
        # t_resolve = time.time()
        self.resolve_dependencies()
        # print(f"✅ Resolved Dependencies in {time.time() - t_resolve:.2f} seconds")
        
        # end_time = time.time()
        # print(f"Took {end_time - start_time:.2f} seconds to parse project files")
        
        if use_cache and self.registry:
            self.load_cache()
        # else:
        #     print("❌ Skipping cache load")
        
        await self.resolve_descriptions()

    async def _parse_single_file(self, filepath: Path):
        if filepath.is_file():
            # Filter out ignored directories
            ignore_list = {"venv", ".venv", "env", ".env", "build", "dist", "__pycache__", ".toaster"}
            if any(part in filepath.parts for part in ignore_list):
                return None

            code = filepath.read_bytes()
            name = filepath.name
            file_obj = await asyncio.to_thread(self.parse_file, name, code)
            if file_obj:
                file_obj.source_path = filepath.relative_to(self.path)
                return file_obj
        return None
    
    async def parse_path(self, path: Path):
        if path.is_file():
            self.files.append(await self._parse_single_file(path))
        else:
            tasks = [self._parse_single_file(filepath) for filepath in path.rglob("*")]
            results = await asyncio.gather(*tasks)
            self.files.extend(filter(None, results))
    
    async def parse_relative_path(self, subpath):
        path = self.path / subpath if subpath else self.path
        await self.parse_path(path)
    
    async def parse_filetree(self, subpath=None):
        path = self.path / subpath if subpath else self.path
        
        if self.path.is_file():
            self.files.append(await self._parse_single_file(path))
        else:
            tasks = [self._parse_single_file(filepath) for filepath in path.rglob("*")]
            results = await asyncio.gather(*tasks)
            self.files.extend(filter(None, results))

    @abstractmethod
    def parse_file(self, name: str, code: bytes) -> BaseFile:
        pass
    
    def resolve_dependencies(self) -> None:
        for file in self.files:
            file.resolve_dependencies()
    
    def load_cache(self):
        # print("Attempting to load cache from SQLite database...")
        # t_cache = time.time()
        self.registry.load_cache()
        # print(f"✅ Loaded Cache in {time.time() - t_cache:.2f} seconds")
                    
    async def resolve_descriptions(self):
        self.visited_ucids = set()
        coroutine_list = [file.resolve_descriptions(self.llm, self.visited_ucids) for file in self.files]
        result = await asyncio.gather(*coroutine_list)
        
        
    def write_skeleton(self):
        toast_string = toast.dump_parser(self, verbosity=Verbosity.SIMPLE)
        toaster_dir = self.path / ".toaster"
        toaster_dir.mkdir(exist_ok=True)
        with open(toaster_dir / "skeleton.toast", "w") as file:
            file.write(toast_string)
            
    def write_cache(self):
        # print("Writing AST to SQLite database...")
        self.registry.save_to_db(self.files)