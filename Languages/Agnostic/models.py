from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class BaseFile(ABC):
    """
    Abstract representation of a source code file.
    Acts as the root container for the dependency graph.
    """
    def __init__(self, ufid: str, imports: List[str], classes: List["BaseClass"]):
        self.ufid = ufid          # Unique File ID (usually filename or relative path)
        self.imports = imports    # List of import strings
        self.classes = classes    # Top-level classes defined in this file

    @classmethod
    @abstractmethod
    def from_source(cls, filename: str, source_code: bytes) -> "BaseFile":
        """Factory method to parse raw source code."""
        pass

    def resolve_dependencies(self):
        """Triggers dependency resolution for all children."""
        for cls in self.classes:
            cls.resolve_dependencies(self.imports)

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

    @classmethod
    @abstractmethod
    def from_node(cls, node: Any, scope: str = "") -> "BaseClass":
        """Factory method to parse an AST node."""
        pass

    def resolve_dependencies(self, imports: List[str]):
        """Passes context to methods to link dependencies."""
        for method in self.methods.values():
            method.resolve_dependencies(imports)
        pass

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
    def __init__(self, umid: str, signature: str, body: str, body_hash: str, dependency_names: List[str]):
        self.umid = umid            # Unique Method ID (e.g. "com.pkg.Class#method(int)")
        self.signature = signature  # Display signature (e.g. "public void method(int a)")
        self.body = body            # Raw source code
        self.body_hash = body_hash  # Hash for diffing
        
        # LLM Output
        self.description = ""
        self.confidence = 0         # 0-100 score

        # Graph Links
        self.dependency_names = dependency_names # Raw strings found in parsing
        self.dependencies: List["BaseMethod"] = [] # Resolved object references

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
            "signature": self.signature,
            "description": self.description,
            "confidence": self.confidence,
            "dependencies": [d.umid for d in self.dependencies] # Only store IDs to prevent cycles
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.umid}>"


class BaseField(ABC):
    """
    Abstract representation of a variable/property.
    """
    def __init__(self, ucid: str, name: str, signature: str):
        self.ucid = ucid            # Unique ID (e.g. "com.pkg.Class.myField")
        self.name = name            # Short name (e.g. "myField")
        self.signature = signature  # Display string (e.g. "private int myField = 5")

    @classmethod
    @abstractmethod
    def from_node(cls, node: Any, scope: str = "") -> "BaseField":
        pass

    def __str__(self) -> str:
        return self.signature

    def __json__(self):
        return {
            "ucid": self.ucid,
            "name": self.name,
            "signature": self.signature
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