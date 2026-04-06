from tree_sitter import Language, Parser
from abc import ABC, abstractmethod
from pathlib import Path

from toaster.core.models import *
from toaster.core.registry import Registry

class BaseBuilder(ABC):
    def __init__(self, registry: Registry):
        self.registry = registry
    
    def with_type(self, struct_type: str) -> "BaseBuilder":
        match(struct_type):
            case "BaseFile": return self.build_file()
            case "BaseClass": return self.build_class()
            case "BaseMethod": return self.build_method()
            case "BaseField": return self.build_field()
        
    @abstractmethod
    def build_file(self) -> "BaseFileBuilder": return BaseFileBuilder(self.registry)
    
    @abstractmethod
    def build_class(self) -> "BaseClassBuilder": return BaseClassBuilder(self.registry)
    
    @abstractmethod
    def build_method(self) -> "BaseMethodBuilder": return BaseMethodBuilder(self.registry)
    
    @abstractmethod
    def build_field(self) -> "BaseFieldBuilder": return BaseFieldBuilder(self.registry)
    
class BaseStructBuilder(ABC):
    def __init__(self, registry: Registry):
        self.registry = registry
        
    @abstractmethod
    def from_dict(self, d: dict) -> BaseStruct: pass

class BaseFileBuilder(BaseStructBuilder):
        
    def from_path(self, path: Path, parent: BaseStruct=None) -> BaseFile:
        file_obj = BaseFile(
            name=path.name,
            uid=str(path),
            path=path,
            registry=self.registry
        )
        return file_obj
    
    def from_dict(self, d: dict) -> BaseFile:
        return BaseFile(**d)

class BaseCodeStructBuilder(BaseStructBuilder):
    @abstractmethod
    def from_node(self, node: Node, parent: BaseStruct=None) -> BaseClass:
        pass

class BaseClassBuilder(BaseCodeStructBuilder):
    def from_dict(self, d: dict) -> BaseClass:
        return BaseClass(**d)

class BaseMethodBuilder(BaseCodeStructBuilder):
    def from_dict(self, d: dict) -> BaseMethod:
        return BaseMethod(**d)

class BaseFieldBuilder(BaseCodeStructBuilder):
    def from_dict(self, d: dict) -> BaseField:
        return BaseField(**d)
    
    