import os
from collections import defaultdict
from tree_sitter import Node, Query, QueryCursor, Language, Parser

from Languages.Java.queries import DEPENDENCY_QUERY
from Languages.Java.language import JAVA_LANGUAGE

from member_registry import MemberRegistry
from Languages.Agnostic import BaseFile, BaseClass, BaseMethod, BaseField, BaseEnum, BaseParser


class JavaFile(BaseFile):
    def __init__(self, filename: str, package: str, imports: list[str], classes: list["JavaClass"]):
        super().__init__(filename, package, imports)
        self.classes = classes
        

    @classmethod
    def from_source(cls, filename: str, source_code: bytes) -> "JavaFile":
        parser = Parser()
        parser.language = JAVA_LANGUAGE
        tree = parser.parse(source_code)
        root_node = tree.root_node
        
        package = ""
        imports = []
        classes = []

        # 1. Iterate top-level nodes for Package, Imports, and Classes
        for child in root_node.children:
            # Extract Package
            if child.type == "package_declaration":
                # package com.example; -> child[1] is the identifier
                # We look for scoped_identifier or identifier
                for grandchild in child.children:
                    if grandchild.type in {"scoped_identifier", "identifier"}:
                        package = grandchild.text.decode('utf-8')
                        break
            
            # Extract Imports
            elif child.type == "import_declaration":
                # import java.util.List;
                for grandchild in child.children:
                    if grandchild.type in {"scoped_identifier", "identifier"}:
                        imports.append(grandchild.text.decode('utf-8'))
            
            # Extract Classes
            elif child.type == "class_declaration":
                # We pass the 'package' we found earlier so the class knows its full name
                java_class = JavaClass.from_node(child, package)
                classes.append(java_class)

        return cls(filename, package, imports, classes)

    @classmethod
    def from_file(cls, filepath: str) -> "JavaFile":
        """Helper to read a file from disk and parse it."""
        with open(filepath, "rb") as f:
            source = f.read()
        return cls.from_source(os.path.basename(filepath), source)

    def resolve_dependencies(self):
        """
        Passes the file's imports to every method in every class 
        so they can resolve their dependencies.
        """
        for java_class in self.classes:
            java_class.resolve_dependencies()

    def __iter__(self):
        return iter(self.classes)

    def __str__(self):
        return f"File: {self.package+'.'+self.filename if self.package else self.filename}" + "\n\t".join([str(c) for c in self.classes])



class JavaClass(BaseClass):
    
    ACCESS_MODIFIERS = {"public", "protected", "private"}
    
    def __init__(self, identifier: str, name: str, modifiers: list[str] = [], body: str = "", 
                 superclass: str = None, interfaces: list[str] = [], type_parameters: list[str] = [], 
                 child_classes: list["JavaClass"] = []):
        super().__init__(identifier, name, body, child_classes)
        
        self.modifiers_list = modifiers
        self.superclass = superclass
        self.interfaces = interfaces
        self.type_parameters = type_parameters
        
        self._process_modifiers()
    
    @classmethod
    def from_node(cls, node: Node, package: str, parent_class: "JavaClass" = None) -> "JavaClass":
        name: str                           = ""
        body_node: Node                     = None
        body: str                           = ""
        superclass: str                     = None
        modifiers: list[str]                = []
        interfaces: list[str]               = []
        type_parameters                     = []
        child_classes: list["JavaClass"]    = []
        
        # name
        identifier_node = node.child_by_field_name('name')
        identifier = identifier_node.text.decode('utf-8')
        if parent_class:
            name = f"{parent_class.name}.{identifier}"
        else:
            name = f"{package}.{identifier}" if package else identifier
        
        for child in node.children:
            match child.type:
                case "modifiers":
                    modifiers_txt = child.text.decode('utf-8')
                    modifiers = modifiers_txt.split()
                case "class_body":
                    body_node = child
                    body = child.text.decode('utf-8')
                case "superclass":
                    for grandchild in child.children:
                        if grandchild.type in {"type_identifier", "scoped_type_identifier", "generic_type"}:
                            superclass = grandchild.text.decode('utf-8')
                case "super_interfaces":
                    type_list_node = None
                    for grandchild in child.children:
                            if grandchild.type == "type_list":
                                type_list_node = grandchild
                                break
                    if type_list_node:
                        for i_node in type_list_node.children:
                            if i_node.type in {"type_identifier", "scoped_type_identifier", "generic_type"}:
                                interfaces.append(i_node.text.decode('utf-8'))
                case "type_parameters":
                    for grandchild in child.children:
                        if grandchild.type == "type_parameter":
                            type_parameters.append(grandchild.text.decode('utf-8'))
                
        instance = cls(
            identifier=identifier,
            name=name, 
            modifiers=modifiers, 
            body=body, 
            superclass=superclass, 
            interfaces=interfaces, 
            type_parameters=type_parameters,
            child_classes=child_classes
        )
        
        # build and attach members
        for child in body_node.children:
            if child.type == "method_declaration" or child.type == "constructor_declaration":
                method = JavaMethod.from_node(child, instance.name)
                instance.methods[method.identifier].append(method)
                MemberRegistry.add_method(method)
            if child.type == "field_declaration":
                field = JavaField.from_node(child, instance.name)
                instance.fields[field.identifier] = field
            if child.type == "enum_declaration":
                enum_obj = JavaEnum.from_node(child, package, parent_class=instance.name)
                instance.child_classes.append(enum_obj)
            if child.type == "class_declaration":
                    child_class = JavaClass.from_node(child, package, parent_class=instance)
                    child_classes.append(child_class)
            
        return instance
    
    def _process_modifiers(self) -> None:
        self.marker_annotation = ""
        self.access_level = "protected"
        self.is_final = False
        self.is_abstract = False
        self.is_static = False
        
        for mod in self.modifiers_list:
            if mod in self.ACCESS_MODIFIERS:
                self.access_level = mod
            if mod == "final":
                self.is_final = True
            if mod == "abstract":
                self.is_abstract = True
            if mod == "static":
                self.is_static = True
            if mod[0] == "@":
                self.marker_annotation = mod
                
        # build final class signature string
        self.signature = f"class {self.identifier}"
        if self.type_parameters:
            self.signature += f"<{', '.join(self.type_parameters)}>"
        parts = [
            self.marker_annotation,                     # @Override
            self.access_level,                          # public
            "abstract" if self.is_abstract else None,   # abstract
            "static" if self.is_static else None,       # static
            "final" if self.is_final else None,         # final
            self.signature,                             # class MyClass
        ]
        if self.superclass:
            parts.append(f"extends {self.superclass}")
        if self.interfaces:
            parts.append(f"implements {', '.join(self.interfaces)}")
        
        self.signature = " ".join(filter(None, parts))
        
    def get_methods(self) -> list["JavaMethod"]:
        all_methods = []
        for m_list in self.methods.values():
            all_methods.extend(m_list)
        return all_methods
    
    def resolve_dependencies(self):
        return super().resolve_dependencies()

    def get_fields(self):
        return list(self.fields.values())
    
    def get_members(self):
        return self.get_fields() + self.get_methods()
    
    def __iter__(self):
        return iter(self.methods.values())
    
    def __getitem__(self, key):
        return self.methods[key]
    
    def __str__(self):
        return "\n" + self.signature + "\n\t" + "\n\t".join([str(member) for member in self.get_members()]) + "\n".join([str(c) for c in self.child_classes])
    __repr__ = __str__
    
    
    
    
class JavaField(BaseField):
    ACCESS_MODIFIERS = {"public", "protected", "private"}

    def __init__(self, identifier: str, name: str, type_name: str, modifiers_list: list[str], 
                 value: str = None):
        super().__init__(identifier, name, type_name)
        self.modifiers_list = modifiers_list
        self.value = value
        
        
        self._process_modifiers()

    @classmethod
    def from_node(cls, node: Node, class_name: str) -> "JavaField":
        identifier = "Unknown"
        type_name = "Unknown"
        modifiers_list = []
        value = None
        
        
        # type
        type_node = node.child_by_field_name('type')
        if type_node:
            type_name = type_node.text.decode('utf-8')
            
        # modifiers
        for child in node.children:
            if child.type == 'modifiers':
                modifiers_str = child.text.decode('utf-8')
                modifiers_list = modifiers_str.split()
                break
        
        # declarator
        declarator = None
        for child in node.children:
            if child.type == 'variable_declarator':
                declarator = child
                break
                
        if declarator:
            # Get Identifier
            name_node = declarator.child_by_field_name('name')
            if name_node:
                identifier = name_node.text.decode('utf-8')
            
            # Get Value (if initialized)
            value_node = declarator.child_by_field_name('value')
            if value_node:
                value = value_node.text.decode('utf-8')
        
        full_name = f"{class_name}.{identifier}"

        return cls(
            identifier=identifier,
            name=full_name,
            type_name=type_name,
            modifiers_list=modifiers_list,
            value=value
        )

    def _process_modifiers(self) -> None:
        self.access_level       = "package-private"
        self.is_final           = False
        self.is_static          = False
        self.is_abstract        = False # Fields generally aren't abstract, but good to have
        self.is_volatile        = False
        self.marker_annotation  = ""
        
        for mod in self.modifiers_list:
            if mod.startswith('@'):
                self.marker_annotation = mod
            if mod in self.ACCESS_MODIFIERS:
                self.access_level = mod
            match mod:
                case "final":
                    self.is_final = True
                case "abstract":
                    self.is_abstract = True
                case "static":
                    self.is_static = True
                case "volatile":
                    self.is_volatile = True
        
        # Build Signature
        self.signature = f"{self.type} {self.identifier}"
        
        parts = [
            self.marker_annotation,
            self.access_level if self.access_level!='package-private' else None,
            "abstract" if self.is_abstract else None,
            "static" if self.is_static else None,
            "final" if self.is_final else None,
            "volatile" if self.is_volatile else None,
            self.signature,
        ]
        
        self.signature = " ".join(filter(None, parts))
        
        # Append value if it exists (e.g. public int x = 5)
        if self.value:
            self.signature += f" = {self.value}"

    def __str__(self):
        return self.signature
    __repr__ = __str__



class JavaMethod(BaseMethod):
    
    _DEP_QUERY = Query(JAVA_LANGUAGE, DEPENDENCY_QUERY)
    
    ACCESS_MODIFIERS = {"public", "protected", "private"}
    
    def __init__(self, class_name: str, identifier: str, name: str, return_type: str, modifiers_list: list[str],
                 type_parameters: list[str], parameters: list[str], body_node: Node, body: str, throws: str = None):
        super().__init__(class_name,identifier, name, return_type, parameters)
        
        self.modifiers_list = modifiers_list
        self.type_parameters = type_parameters
        self.body_node = body_node
        self.body = body
        self.throws = throws
        
        self._process_modifiers()
    
    @classmethod
    def from_node(cls, node: Node, class_name: str) -> "JavaMethod":
        identifier: str                 = ""
        name: str                       = ""
        return_type: str                = ""
        modifiers_list: list[str]       = []
        type_parameters: list[str]      = []
        parameters: list[str]           = []
        body_node: Node                 = None
        body: str                       = ""
        throws: str                     = None
        
        # identifier
        identifier_node = node.child_by_field_name('name')
        identifier: str = identifier_node.text.decode('utf-8') if identifier_node else "<init>"
        name = f"{class_name}.{identifier}"
        
        # return type
        type_node = node.child_by_field_name('type')
        if type_node:
            return_type = type_node.text.decode('utf-8')
        elif node.type == 'constructor_declaration':
            return_type = class_name
        else:
            return_type = "void"
            
        # modifiers and type parameters
        for child in node.children:
            if child.type == 'modifiers':
                modifiers_str = child.text.decode('utf-8')
                modifiers_list = modifiers_str.split()
            if child.type == 'type_parameters':
                for grandchild in child.children:
                    if grandchild.type == "type_parameter":
                        type_parameters.append(grandchild.text.decode('utf-8'))
            if child.type == "throws":
                throws = child.text.decode('utf-8')
        
        # parameters
        params_node = node.child_by_field_name('parameters')
        if params_node:
            for child in params_node.children:
                if child.type in {"formal_parameter", "spread_parameter"}:
                    parameters.append(child.text.decode('utf-8'))
                    
        # body
        body_node = node.child_by_field_name('body')
        if body_node:
            body = body_node.text.decode('utf-8')
        
        instance = cls(
            class_name = class_name,
            identifier = identifier,
            name = name,
            return_type = return_type,
            modifiers_list = modifiers_list,
            type_parameters = type_parameters,
            parameters = parameters,
            body_node = body_node,
            body = body,
            throws = throws
        )
        
        return instance
    
    def _process_modifiers(self) -> None:
        self.access_level       = "package-private"
        self.is_final           = False
        self.is_static          = False
        self.is_abstract        = False
        self.is_synchronized    = False
        self.marker_annotation  = ""
        
        for mod in self.modifiers_list:
            if mod[0] == '@':
                self.marker_annotation = mod
            if mod in self.ACCESS_MODIFIERS:
                self.access_level = mod
            match mod:
                case "final":
                    self.is_final = True
                case "abstract":
                    self.is_abstract = True
                case "static":
                    self.is_static = True
                case "synchronized":
                    self.is_synchronized = True
        
        self.signature = f"{self.return_type} {self.identifier}"
        if self.type_parameters:
            self.signature += f"<{', '.join(self.type_parameters)}>"
        self.signature += f"({', '.join(self.parameters)})"
        parts = [
            self.marker_annotation,                                                 # @Override
            self.access_level if self.access_level!='package-private' else None,    # public
            "abstract" if self.is_abstract else None,                               # abstract
            "static" if self.is_static else None,                                   # static
            "final" if self.is_final else None,                                     # final
            "synchronized" if self.is_synchronized else None,                       # synchronized
            self.signature,                                                         # void MyMethod<T>()
            self.throws,                                                            # throws Exception
        ]
        self.signature = " ".join(filter(None, parts))
    
    
    def resolve_dependencies(self, imports: list[str] = []) -> None:
        if not self.body_node: 
            return
        
        query_cursor = QueryCursor(self._DEP_QUERY)
        captures = query_cursor.captures(self.body_node)
        
        dependency_names = set()
        if "dependencies" in captures:
            for node in captures["dependencies"]:
                dependency_names.add(node.text.decode('utf-8'))
        
        if not dependency_names:
            return
        
        # try to find the dependencies in the member_registry
        for name in dependency_names:
            # try local first
            local_fullname = self.class_name + "." + name
            if local_fullname in MemberRegistry.methods.keys():
                self.dependencies.append(MemberRegistry.methods[local_fullname])
                print("RESOLVED DEPENDENCY: to " + str(MemberRegistry.methods[local_fullname]) + f" (fullname {local_fullname} in registry)")
                continue
            
            # then imports
            for i in imports:
               import_fullname = i + "." + name
               if import_fullname in MemberRegistry.methods.keys():
                   self.dependencies.append(MemberRegistry.methods[import_fullname])
                   print("RESOLVED DEPENDENCY: to " + str(MemberRegistry.methods[import_fullname]) + f" (imported fullname {import_fullname} in registry)")
                   continue
            
            # if there is only one method called [name] in registry
            if len(MemberRegistry.methods_by_name[name]) == 1:
                self.dependencies.append(MemberRegistry.methods_by_name[name][0])
                print("RESOLVED DEPENDENCY: to " + str(MemberRegistry.methods_by_name[name][0]) + f" (only one {name} in registry)")
                continue
            
            # wasnt resolved, so just return all that we have
            self.dependencies.extend(MemberRegistry.methods_by_name[name])
            
        
    def __str__(self) -> str:
        return self.signature.strip()
    __repr__ = __str__



class JavaEnum(BaseEnum):
    ACCESS_MODIFIERS = {"public", "protected", "private"}

    def __init__(self, identifier: str, name: str, constants: list[str], modifiers: list[str] = [], 
                 body: str = "", interfaces: list[str] = []):
        
        super().__init__(identifier, name, body, constants)
        self.modifiers_list = modifiers
        self.interfaces = interfaces
        self._process_modifiers()

    @classmethod
    def from_node(cls, node: Node, package: str, parent_class: str = "") -> "JavaEnum":
        identifier = ""
        name = ""
        body_node = None
        body = ""
        modifiers = []
        interfaces = []
        constants = []
        
        # identifier and name
        identifier_node = node.child_by_field_name('name')
        if identifier_node:
            identifier = identifier_node.text.decode('utf-8')
        
        if parent_class:
            name = f"{parent_class}.{identifier}"
        else:
            name = f"{package}.{identifier}" if package else identifier

        # declaration parts (modifiers, interfaces, body)
        for child in node.children:
            match child.type:
                case "modifiers":
                    modifiers = child.text.decode('utf-8').split()
                case "super_interfaces":
                    # Enums implements interfaces
                    for grandchild in child.children:
                         if grandchild.type == "type_list":
                            for i_node in grandchild.children:
                                if i_node.type in {"type_identifier", "scoped_type_identifier"}:
                                    interfaces.append(i_node.text.decode('utf-8'))
                case "enum_body":
                    body_node = child
                    body = child.text.decode('utf-8')

        instance = cls(identifier, name, constants, modifiers, body, interfaces)

        # body
        if body_node:
            for child in body_node.children:
                if child.type == "enum_constant":
                    # Extract "PROCESSING" or "PROCESSING(1)"
                    constant_name = child.child_by_field_name('name').text.decode('utf-8')
                    
                    # Check for arguments: PROCESSING(1, "test")
                    args_node = child.child_by_field_name('arguments')
                    if args_node:
                        args_text = args_node.text.decode('utf-8')
                        instance.constants.append(f"{constant_name}{args_text}")
                    else:
                        instance.constants.append(constant_name)

                elif child.type in {"method_declaration", "constructor_declaration"}:
                    method = JavaMethod.from_node(child, instance.name)
                    instance.methods[method.identifier].append(method)
                    MemberRegistry.add_method(method)
                
                elif child.type == "field_declaration":
                    field = JavaField.from_node(child, instance.name)
                    instance.fields[field.identifier] = field

        return instance

    def _process_modifiers(self) -> None:
        self.access_level = "package-private"
        self.is_static = False
        
        for mod in self.modifiers_list:
            if mod in self.ACCESS_MODIFIERS:
                self.access_level = mod
            if mod == "static":
                self.is_static = True
        
        self.signature = f"enum {self.identifier}"
        
        parts = [
            self.access_level if self.access_level != "package-private" else None,
            "static" if self.is_static else None,
            self.signature
        ]
        
        base_sig = " ".join(filter(None, parts))
        
        if self.interfaces:
            base_sig += f" implements {', '.join(self.interfaces)}"
            
        self.signature = base_sig
    
    def resolve_dependencies(self):
        super.resolve_dependences()