from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from member_registry import MemberRegistry
import json
import asyncio

class BaseFile(ABC):
    """
    Abstract representation of a source code file.
    Acts as the root container for the dependency graph.
    """
    
    id = 0
    def __init__(self, ufid: str, imports: List[str], classes: List["BaseClass"]):
        self.ufid = ufid          # Unique File ID (usually filename or relative path)
        self.imports = imports    # List of import strings
        self.classes = classes    # Top-level classes defined in this file

        self.id = BaseFile.id
        BaseFile.id += 1
        
    @classmethod
    @abstractmethod
    def from_source(cls, filename: str, source_code: bytes) -> "BaseFile":
        """Factory method to parse raw source code."""
        pass

    def resolve_dependencies(self):
        """Triggers dependency resolution for all children."""
        for cls in self.classes:
            cls.resolve_dependencies(self.imports)
    
    async def resolve_descriptions(self, llm: "LLMClient", visited_ucids: set[str] = None):
        if visited_ucids is None:
            visited_ucids = set()
        coroutine_list = [cls.resolve_descriptions(llm, self.imports, visited_ucids) for cls in self.classes]
        for class_obj in self.classes:
            coroutine_list.extend([c.resolve_descriptions(llm, self.imports, visited_ucids) for c in class_obj.child_classes.values()])
        await asyncio.gather(*coroutine_list)

    def __json__(self):
        return {
            "ufid": self.ufid,
            "imports": self.imports,
            "classes": [c.__json__() for c in self.classes]
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.ufid}>"


class BaseClass(ABC):
    """
    Abstract representation of a Class.
    Stores Members (Fields/Methods) and Metadata for LLM processing.
    """
    
    id = 0
    def __init__(self, ucid: str, signature: str, body: str):
        self.ucid = ucid            # Unique Context ID (e.g. "com.pkg.MyClass")
        self.signature = signature  # Display signature (e.g. "public class MyClass extends B")
        self.body = body            # Raw source code
        
        # Change Detection & LLM
        self.body_hash = ""         
        self.description = ""       

        # Children (Keyed by ID for O(1) access)
        self.fields: Dict[str, "BaseField"] = {}
        self.methods: Dict[str, "BaseMethod"] = {}
        self.child_classes: Dict[str, "BaseClass"] = {}
        
        self.id = BaseClass.id
        BaseClass.id += 1
        
        self.sent_to_llm = False

    @classmethod
    @abstractmethod
    def from_node(cls, node: Any, scope: str = "") -> "BaseClass":
        """Factory method to parse an AST node."""
        pass

    def resolve_dependencies(self, imports: List[str] = []):
        """Passes context to methods to link dependencies."""
        for method in self.methods.values():
            method.resolve_dependencies(imports)
        for child in self.child_classes.values():
            child.resolve_dependencies(imports)
    
    async def resolve_descriptions(self, llm: "LLMClient", imports: List[str] = None, visited_ucids: set[str] = None):
        if imports is None: imports = []
        if visited_ucids is None: visited_ucids = set()
        
        if self.ucid in visited_ucids:
            return
        visited_ucids.add(self.ucid)
        
        needs_description = any([not method.description for method in self.methods.values()])
        if not needs_description:
            # print(f"No changes in {self.ucid}, skipping llm call")
            return
        
        try:
            response_obj = await llm.generate_description(self, imports)
            
            if not response_obj or response_obj.get("status") == "error":
                error_msg = response_obj.get('error') if response_obj else 'Returned None'
                print(f"⚠️ Skipping {self.ucid} due to LLM failure: {error_msg}")
                return
            
            self.description = response_obj["description"]
            self.confidence = response_obj["confidence"]
            # extract method level descriptions
            for method_obj in response_obj["methods"]:
                returned_umid = method_obj["umid"]
                
                method = self.methods.get(returned_umid)
                
                if method:
                    method.description = method_obj["description"]
                    method.confidence = method_obj["confidence"]
        except Exception as e:
            print(f"Failed to generate description for {self.ucid} with response {response_obj}: {e}")
        # determine which methods need second pass

    def __json__(self):
        return {
            "ucid": self.ucid,
            "signature": self.signature,
            "description": self.description,
            "fields": [f.__json__() for f in self.fields.values()],
            "methods": [m.__json__() for m in self.methods.values()],
            "child_classes": [c.__json__() for c in self.child_classes.values()]
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.ucid}>"


class BaseMethod(ABC):
    """
    Abstract representation of a Function/Method.
    This is the primary unit of work for the LLM.
    """
    id = 0
    def __init__(self, identifier: str, scoped_identifier: str, return_type: str, umid: str, signature: str, body: str, body_hash: str, dependency_names: List[str], line: int, parameters: List[str]):
        self.identifier = identifier
        self.return_type = return_type
        self.scoped_identifier = scoped_identifier
        self.umid = umid            # Unique Method ID (e.g. "com.pkg.Class#method(int)")
        self.signature = signature  # Display signature (e.g. "public void method(int a)")
        self.body = body            # Raw source code
        self.body_hash = body_hash  # Hash for diffing
        self.line = line #line number in file
        self.parameters = parameters
        self.arity = len(self.parameters)
        self.id = BaseMethod.id
        BaseMethod.id += 1
        
        # LLM Output
        self.description = ""
        self.confidence = 0         # 0-100 score

        # Graph Links
        self.dependency_names = dependency_names # Raw strings found in parsing
        self.dependencies: List["BaseMethod"] = [] # Resolved object references
        self.unresolved_dependencies: List[str] = []

    @classmethod
    @abstractmethod
    def from_node(cls, node: Any, scope: str, dep_query: Any = None) -> "BaseMethod":
        """Factory method to parse an AST node."""
        pass

    @abstractmethod
    def resolve_dependencies(self, imports: List[str]):
        """Links dependency_names to actual BaseMethod objects."""
        pass

    def __str__(self) -> str:
        return self.signature

    def __json__(self):
        return {
            "umid": self.umid,
            "return_type": self.return_type if self.return_type else "None",
            "line": self.line,
            "signature": self.signature,
            "body_hash": self.body_hash,
            "description": self.description,
            "dependencies": self.dependencies,
            "unresolved_dependencies": self.unresolved_dependencies
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.umid}>"


class BaseField(ABC):
    """
    Abstract representation of a variable/property.
    """
    def __init__(self, ucid: str, name: str, signature: str, field_type: str):
        self.ucid = ucid            # Unique ID (e.g. "com.pkg.Class.myField")
        self.name = name            # Short name (e.g. "myField")
        self.signature = signature  # Display string (e.g. "private int myField = 5")
        self.field_type = field_type

    @classmethod
    @abstractmethod
    def from_node(cls, node: Any, scope: str = "") -> "BaseField":
        pass

    def __str__(self) -> str:
        return self.signature

    def __json__(self):
        return {
            "name": self.name,
            "field_type": self.field_type
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.ucid}>"


class BaseEnum(BaseClass):
    """
    Abstract representation of an Enumeration.
    """
    def __init__(self, ucid: str, signature: str, body: str, constants: List[str]):
        super().__init__(ucid, signature, body)
        self.constants = constants # ["VAL1", "VAL2(args)"]

    def __json__(self):
        data = super().__json__()
        data["constants"] = self.constants
        return data