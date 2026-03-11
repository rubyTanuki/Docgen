from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import re
import json
import asyncio
import hashlib

from toaster.core.registry import MemberRegistry

@dataclass
class BaseFile(ABC):
    """
    Abstract representation of a source code file.
    Acts as the root container for the dependency graph.
    """
    ufid: str # Unique File ID (usually filename or relative path)
    imports: List[str]
    classes: List["BaseClass"]
    registry: MemberRegistry = None
    
    id: str = field(init=False)

    def __post_init__(self):
        id_hash = hashlib.md5(self.ufid.encode('utf-8')).hexdigest()[:4]
        self.id = f"F-{id_hash}"

    def resolve_dependencies(self):
        """Triggers dependency resolution for all children."""
        for c in self.classes:
            c.resolve_dependencies(self.imports)
    
    async def resolve_descriptions(self, llm: "LLMClient", visited_ucids: set[str] = None):
        if visited_ucids is None:
            visited_ucids = set()
        coroutine_list = [cls.resolve_descriptions(llm, self.imports, visited_ucids, self.registry) for cls in self.classes]
        for class_obj in self.classes:
            coroutine_list.extend([c.resolve_descriptions(llm, self.imports, visited_ucids, self.registry) for c in class_obj.child_classes.values()])
        await asyncio.gather(*coroutine_list)

    def __str__(self):
        return f"<{self.__class__.__name__}: {self.ufid}>"
    __repr__=__str__


@dataclass
class BaseClass(ABC):
    """
    Abstract representation of a Class.
    Stores Members (Fields/Methods) and Metadata for LLM processing.
    """
    ucid: str
    signature: str
    body: str
    start_line: int
    node: Any = None
    registry: MemberRegistry = None
    
    # computed
    end_line: int = field(init=False)
    id: str = field(init=False)
    description: str = ""
    sent_to_llm: bool = False
    constants: List[str] = field(default_factory=list)
    confidence: float = 0.0
    
    fields: Dict[str, "BaseField"] = field(default_factory=dict)
    methods: Dict[str, "BaseMethod"] = field(default_factory=dict)
    child_classes: Dict[str, "BaseClass"] = field(default_factory=dict)

    def __post_init__(self):
        self.end_line = self.start_line + self.body.count('\n')
        self.id = f"C-{hashlib.md5(self.ucid.encode('utf-8')).hexdigest()[:4]}"
        
    @abstractmethod
    def skeletonize(self) -> str:
        pass

    def resolve_dependencies(self, imports: List[str] = None):
        if imports is None:
            imports = []
        """Passes context to methods to link dependencies."""
        for method in self.methods.values():
            method.resolve_dependencies(imports)
        for child in self.child_classes.values():
            child.resolve_dependencies(imports)
    
    async def resolve_descriptions(self, llm: "LLMClient", imports: List[str] = None, visited_ucids: set[str] = None, registry=None):
        if imports is None: imports = []
        if visited_ucids is None: visited_ucids = set()
        self.registry = registry or self.registry
        
        if self.ucid in visited_ucids:
            return
        visited_ucids.add(self.ucid)
        
        needs_description = any([not method.description for method in self.methods.values()]) or not self.description
        if not needs_description:
            return
        
        try:
            response_obj = await llm.generate_description(self, imports)
            
            if not response_obj or response_obj.get("status") == "error":
                error_msg = response_obj.get('error') if response_obj else 'Returned None'
                print(f"⚠️ Skipping {self.ucid} due to LLM failure: {error_msg}")
                return
            
            self.description = response_obj["description"]
            self.confidence = response_obj["confidence"]
            
            if self.registry:
                self.registry.update_class_description(self)
                
            for method_obj in response_obj.get("methods", []):
                returned_umid = method_obj.get("umid")
                if not returned_umid:
                    continue
                    
                method = self.methods.get(returned_umid)
                if method:
                    method.description = method_obj.get("description", "")
                    method.confidence = method_obj.get("confidence", 0)
                    if self.registry:
                        self.registry.update_method_description(method)
            
        except Exception as e:
            print(f"Failed to generate description for {self.ucid}: {e}")

    def __str__(self):
        return f"<{self.__class__.__name__}: {self.ucid}>"
    __repr__ = __str__


@dataclass
class BaseMethod(ABC):
    """
    Abstract representation of a Function/Method.
    This is the primary unit of work for the LLM.
    """
    identifier: str
    scoped_identifier: str
    return_type: str
    umid: str
    signature: str
    body: str
    dependency_names: List[str]
    start_line: int
    parameters: List[str]
    node: Any = None
    registry: MemberRegistry = None
    file: BaseFile = None
    parent_class: BaseClass = None
    
    # computed
    arity: int = field(init=False)
    body_hash: str = field(init=False)
    id: str = field(init=False)
    end_line: int = field(init=False)
    description: str = ""
    confidence: float = 0.0
    dependencies: List[str] = field(default_factory=list)
    unresolved_dependencies: List[str] = field(default_factory=list)
    inbound_dependencies: List[str] = field(default_factory=list)

    @property
    def impact_score(self) -> int:
        return len(self.inbound_dependencies) * 2 + len(self.dependencies)

    def __post_init__(self):
        self.arity = len(self.parameters)
        clean_body = re.sub(r'\s+', '', self.body)
        self.body_hash = hashlib.sha256(clean_body.encode('utf-8')).hexdigest()[:8]
        self.id = f"M-{hashlib.md5(self.umid.encode('utf-8')).hexdigest()[:5]}" 
        self.end_line = self.start_line + self.body.count('\n')

    @abstractmethod
    def resolve_dependencies(self, imports: List[str]):
        """Links dependency_names to actual BaseMethod objects."""
        pass

    def __str__(self) -> str:
        return f"<{self.__class__.__name__}: {self.umid}>"
    __repr__=__str__


@dataclass
class BaseField(ABC):
    """
    Abstract representation of a variable/property.
    """
    ucid: str
    name: str
    signature: str
    field_type: str

    def __str__(self) -> str:
        return f"<{self.__class__.__name__}: {self.ucid}>"
    __repr__ = __str__