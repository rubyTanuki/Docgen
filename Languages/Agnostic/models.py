from abc import ABC, abstractmethod
from collections import defaultdict
from typing import List, Dict, Any, Optional

class BaseFile(ABC):
    """
    Abstract representation of a source code file.
    Contains Imports, Packages/Namespaces, and Top-Level Classes/Functions.
    """
    def __init__(self, filename: str, package: str = "", imports: List[str] = None):
        self.filename = filename          # e.g., "MyService.java"
        self.package = package            # e.g., "com.example.services"
        self.imports = imports or []      # e.g., ["java.util.List", "java.io.File"]
        
        # Files contain classes (or top-level functions in Python/JS/C)
        self.classes: List["BaseClass"] = []
        
        # Files can technically have top-level fields/methods too (C/Python/JS)
        self.methods: List["BaseMethod"] = [] 
        self.fields: List["BaseField"] = []
        
    @classmethod
    @abstractmethod
    def from_source(cls, filename: str, source_code: bytes) -> "BaseFile":
        """
        Factory method to parse raw source code bytes into a File object.
        """
        pass

    def get_all_classes(self) -> List["BaseClass"]:
        return self.classes

    def __str__(self) -> str:
        filename = self.filename
        if self.package:
            filename = f"{self.package}.{filename}"
        return f"\n{filename}\n    Imports:\n\t{"\n\t".join([imp for imp in self.imports])}\n" + "\n".join([str(c) for c in self.classes])

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.filename}>"
    
    @abstractmethod
    def resolve_dependencies(self):
        for cls in self.classes:
            cls.resolve_dependencies()
        
        for method in self.methods:
            method.resolve_dependencies()
    
    def __json__(self):
        return {
            "filename": self.filename,
            "package": self.package,
            "imports": self.imports,
            "classes": [c.__json__() for c in self.classes],
            "methods": [m.__json__() for m in self.methods],
            "fields": [f.__json__() for f in self.fields]
        }
    def __skeleton__(self):
        obj = {cls.signature: cls.__skeleton__() for cls in self.classes}
        return {k: v for k, v in obj.items() if v}


class BaseField(ABC):
    """
    Abstract representation of a class property/variable.
    """
    def __init__(self, identifier: str, name: str, type_name: str):
        self.identifier = identifier  # Short name (e.g., "myVar")
        self.name = name              # Fully qualified name (e.g., "com.pkg.MyClass.myVar")
        self.type = type_name         # String representation of type (e.g., "int", "List<String>")
        self.signature = ""           # The full display string (e.g., "public int myVar = 0")

    @classmethod
    @abstractmethod
    def from_node(cls, node: Any, parent_name: str) -> "BaseField":
        """
        Factory method to create a Field instance from a Tree-sitter node.
        """
        pass

    def __str__(self) -> str:
        return self.signature

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.name}>"
    
    def __json__(self):
        return {
            "identifier": self.identifier,
            "name": self.name,
            "type": self.type,
            "signature": self.signature
        }
    def __skeleton__(self):
        return self.signature


class BaseMethod(ABC):
    """
    Abstract representation of a function or method.
    """
    def __init__(self, class_name: str, identifier: str, name: str, return_type: str, parameters: List[str]):
        self.class_name = class_name      # Fully qualified class name (e.g., "com.pkg.MyClass")
        self.identifier = identifier      # Short name (e.g., "toString")
        self.name = name                  # Fully qualified name (e.g., "com.pkg.MyClass.toString")
        self.return_type = return_type    # Return type string
        self.parameters = parameters      # List of parameter strings
        self.signature = ""               # Full display string
        self.body = ""                    # The source code of the method body
        
        self.dependencies: List[str] = []

    @classmethod
    @abstractmethod
    def from_node(cls, node: Any, parent_name: str) -> "BaseMethod":
        """
        Factory method to create a Method instance from a Tree-sitter node.
        """
        pass

    @abstractmethod
    def resolve_dependencies(self):
        pass

    def __str__(self) -> str:
        return self.signature

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.name}>"
    
    def __json__(self):
        return {
            "class_name": self.class_name,
            "identifier": self.identifier,
            "name": self.name,
            "return_type": self.return_type,
            "parameters": self.parameters,
            "signature": self.signature,
            # "body": self.body,
            "dependencies": [str(d) for d in self.dependencies]
        }
    def __skeleton__(self):
        return self.signature


class BaseClass(ABC):
    """
    Abstract representation of a Class or Interface.
    Container for Methods and Fields.
    """
    def __init__(self, identifier: str, name: str, body: str, child_classes: List["BaseClass"] = [],):
        self.identifier = identifier
        self.name = name
        self.child_classes: List["BaseClass"] = child_classes
        self.body = body
        self.signature = ""

        # Common storage for children
        self.fields: Dict[str, BaseField] = {}
        self.methods: Dict[str, List[BaseMethod]] = defaultdict(list)

    @classmethod
    @abstractmethod
    def from_node(cls, node: Any, package: str = "") -> "BaseClass":
        """
        Factory method to create a Class instance from a Tree-sitter node.
        """
        pass

    def get_methods(self) -> List[BaseMethod]:
        """Flatten the dictionary of methods into a single list."""
        all_methods = []
        for m_list in self.methods.values():
            all_methods.extend(m_list)
        return all_methods

    @abstractmethod
    def resolve_dependencies(self):
        for method in self.get_methods():
            method.resolve_dependencies()

    def get_fields(self) -> List[BaseField]:
        """Return a list of all fields."""
        return list(self.fields.values())

    def get_members(self) -> List[Any]:
        """Return all children (fields + methods)."""
        return self.get_fields() + self.get_methods()

    # --- Iterator Protocols (So you can do 'for method in my_class') ---
    def __iter__(self):
        return iter(self.methods.values())

    def __getitem__(self, key: str) -> List[BaseMethod]:
        return self.methods[key]

    def __str__(self) -> str:
        members_str = "\n\t".join([str(m) for m in self.get_members()])
        child_classes_str = "\n\t".join([str(c) for c in self.child_classes])
        return f"\n{self.signature}\n\t{members_str}\n\t{child_classes_str}\n"

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.name}>"
    
    def __json__(self):
        return {
            "identifier": self.identifier,
            "name": self.name,
            "signature": self.signature,
            "fields": [f.__json__() for f in self.get_fields()],
            "methods": [m.__json__() for m in self.get_methods()],
            # "body": self.body,
            "child_classes": [c.__json__() for c in self.child_classes],
        }
    def __skeleton__(self):
        obj = {
            "fields": [f.__skeleton__() for f in self.get_fields()],
            "methods": [m.__skeleton__() for m in self.get_methods()],
            "child_classes": [c.__skeleton__() for c in self.child_classes],
        }
        return {k: v for k, v in obj.items() if v}

class BaseEnum(BaseClass):
    """
    Abstract representation of an Enumeration.
    Inherits from BaseClass because Enums can have methods and fields.
    """
    def __init__(self, identifier: str, name: str, body: str, constants: list[str]):
        
        super().__init__(identifier, name, body)
        
        self.constants = constants # List of strings like ["IDLE", "PROCESSING(1)"]
        self.signature = ""

    def __str__(self) -> str:
        constants_str = ", ".join(self.constants)
        members_str = "\n\t".join([str(m) for m in self.get_members()])
        return f"\n{self.signature} {{ {constants_str} }}\n\t{members_str}\n"

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.name}>"
    
    def __json__(self):
        return {
            "identifier": self.identifier,
            "name": self.name,
            "signature": self.signature,
            # "body": self.body,
            "child_classes": [c.__json__() for c in self.child_classes],
            "constants": self.constants
        }
    def __skeleton__(self):
        obj = {
            "signature": self.signature,
            "constants": self.constants,
            "child_classes": [c.__skeleton__() for c in self.child_classes],
        }
        return {k: v for k, v in obj.items() if v}
        