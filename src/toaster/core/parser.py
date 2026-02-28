from pathlib import Path
from abc import ABC, abstractmethod
from collections import defaultdict
import asyncio
import json

from toaster.core.models import BaseFile
from toaster.core.registry import MemberRegistry

class BaseParser(ABC):
    def __init__(self, project_dir: str, llm=None, registry: MemberRegistry=None):
        self.llm = llm
        self.registry = registry
        self.files: list[BaseFile] = []
        self.project_dir = project_dir

    async def parse(self, use_cache=True):
        self.parse_filetree()
        print("✅ Parsed Project Files")
        
        self.resolve_dependencies()
        print("✅ Resolved Dependencies")
        
        if use_cache:
            self.load_cache()
        else:
            print("❌ Skipping cache load")
        
        await self.resolve_descriptions()

    def parse_filetree(self):
        path = Path(self.project_dir)
        
        for filepath in path.rglob("*"):
            if filepath.is_file():
                code = filepath.read_bytes()
                suffix = filepath.suffix
                name = filepath.name
                
                file_obj = self.parse_file(name, code)
            
                if file_obj:
                    file_obj.source_path = filepath 
                    self.files.append(file_obj)
        
    @abstractmethod
    def parse_file(self, name: str, code: bytes) -> BaseFile:
        pass
    
    def resolve_dependencies(self) -> None:
        for file in self.files:
            file.resolve_dependencies()
    
    def load_cache(self):
        cache_file = Path(self.project_dir) / ".toaster_cache.json"
        print(f"Attempting to load cache from {cache_file}")
        if cache_file.exists():
            with open(cache_file, 'r', encoding='utf-8') as f:
                self.registry.load_cache(json.load(f))
        else:
            print(f"Cache not found at {cache_file}")
                    
    async def resolve_descriptions(self):
        self.visited_ucids = set()
        coroutine_list = [file.resolve_descriptions(self.llm, self.visited_ucids) for file in self.files]
        result = await asyncio.gather(*coroutine_list)