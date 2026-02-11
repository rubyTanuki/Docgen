from tree_sitter import Tree, Query, QueryCursor

from language import JAVA_LANGUAGE
from java_method import Method
from java_field import Field

from collections import defaultdict

class Class:
    ACCESS_MODIFIERS = {"public", "protected", "private"}
    def __init__(self, tree: Tree, package: str):
        
        # parse class details
        self.modifiers_txt = ""
        self.modifiers_list = []
        self.body_node = None
        self.body = ""
        self.superclass: str = None
        self.interfaces: list[str] = []
        self.type_parameters = []
        for child in tree.children:
            match child.type:
                case "modifiers":
                    self.modifiers_txt = child.text.decode('utf-8')
                    self.modifiers_list = self.modifiers_txt.split()
                case "class_body":
                    self.body_node = child
                    self.body = child.text.decode('utf-8')
                case "superclass":
                    for grandchild in child.children:
                        if grandchild.type in {"type_identifier", "scoped_type_identifier", "generic_type"}:
                            self.superclass = grandchild.text.decode('utf-8')
                case "super_interfaces":
                    type_list_node = None
                    for grandchild in child.children:
                            if grandchild.type == "type_list":
                                type_list_node = grandchild
                                break
                    if type_list_node:
                        for i_node in type_list_node.children:
                            if i_node.type in {"type_identifier", "scoped_type_identifier", "generic_type"}:
                                self.interfaces.append(i_node.text.decode('utf-8'))
                case "type_parameters":
                    for grandchild in child.children:
                        if grandchild.type == "type_parameter":
                            self.type_parameters.append(grandchild.text.decode('utf-8'))
        
        identifier_node = tree.child_by_field_name('name')
        self.identifier = identifier_node.text.decode('utf-8')
        self.name = package + "." + self.identifier if package != "" else self.identifier
        
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
            
        # extract and build methods, fields, and enums
        self.methods = defaultdict(list[Method])
        self.fields = {}
        for child in self.body_node.children:
            if child.type == "method_declaration" or child.type == "constructor_declaration":
                method = Method(child, self.name)
                self.methods[method.identifier].append(method)
            if child.type == "field_declaration":
                field = Field(child, self.name)
                self.fields[field.identifier] = field
            if child.type == "enum_declaration":
                pass
            
        
    def get_methods(self) -> list[Method]:
        return list(self.methods.values())
    
    def get_fields(self):
        return list(self.fields.values())
    
    def get_members(self):
        return self.get_fields() + self.get_methods()
    
    def __iter__(self):
        return iter(self.methods.values())
    
    def __getitem__(self, key):
        return self.methods[key]
    
    def __str__(self):
        return "\n" + self.signature + "\n\t" + "\n\t".join([str(member) for member in self.get_members()]) + "\n"
    __repr__ = __str__
        
    