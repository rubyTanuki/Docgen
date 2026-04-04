from pathlib import Path
from abc import ABC, abstractmethod
from collections import defaultdict
import asyncio
import json
import time
from collections import deque

from toaster.core.models import BaseFile
from toaster.core.registry import Registry
from toaster.core.serializer import toast, Verbosity

class BaseParser(ABC):
    def __init__(self, project_dir: str, llm=None, registry: Registry=None):
        self.llm = llm
        self.registry = registry
        self.project_path = Path(self.project_dir)
        self.path_ignore = ["venv", ".venv", "env", ".env", "build", "dist", "__pycache__", ".toaster"]
    
    @property
    def files(self):
        if self._files: return self._files
        self._files = self.registry.uid_map.values().Filter(lambda x: isinstance(x, BaseFile)).ToList()
        return self._files
    
    
    async def parse(self, subpath: Path = None):
        if not subpath:
            subpath = self.project_path
        
        # print(f"🔍 Parsing files in '{self.project_dir}' and linking AST...")
        
        # start_time = time.time()
        
        # t_parse = time.time()
        if subpath.is_dir():
            self.registry.root = Directory(path=subpath, registry=self.registry)
            self.registry.add_struct(self.registry.root)
            for path in subpath.glob("*"):
                if any(part in path.parts for part in self.path_ignore):
                    continue
                if path.is_dir():
                    directory = Directory(path=path, registry=self.registry, parent=self.registry.root)
                    self.registry.add_struct(directory)
                    directory.parse_children()
                else:
                    file = self.parse_file(subpath, parent=self.registry.root)
                    self.registry.add_struct(file)
        else:
            file = self.parse_file(subpath)
            self.registry.root = file
            self.registry.add_struct(file)
        # # print(f"✅ Parsed Project Files in {time.time() - t_parse:.2f} seconds")
        
        # # t_resolve = time.time()
        self.registry.root.resolve_dependencies()
        # # print(f"✅ Resolved Dependencies in {time.time() - t_resolve:.2f} seconds")
        
        # # end_time = time.time()
        # # print(f"Took {end_time - start_time:.2f} seconds to parse project files")

    @abstractmethod
    def parse_file(self, subpath: Path) -> BaseFile:
        builder = StructBuilderProvier.get_builder(subpath.suffix, self.registry)
        return builder.build_file.from_path(subpath)
    
    def resolve_dependencies(self) -> None:
        tree_root.resolve_dependencies()
    
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