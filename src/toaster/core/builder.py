from tree_sitter import Language, Parser
from abc import ABC, abstractmethod
from pathlib import Path

from toaster.core.models import *

class BaseBuilder(ABC):
    def __init__(self, registry: MemberRegistry):
        self.registry = registry
        
    @abstractmethod
    def build_file(self) -> "BaseFileBuilder": pass
    
    @abstractmethod
    def build_class(self) -> "BaseCodeStructBuilder": pass
    
    @abstractmethod
    def build_method(self) -> "BaseCodeStructBuilder": pass
    
    @abstractmethod
    def build_field(self) -> "BaseCodeStructBuilder": pass
    
class BaseStructBuilder(ABC):
    def __init__(self, registry: MemberRegistry):
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
    
    