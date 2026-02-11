from tree_sitter import Node, Query, QueryCursor

from queries import FIELD_QUERY
from language import JAVA_LANGUAGE

class JavaField:
    ACCESS_MODIFIERS = {"public", "protected", "private"}
    def __init__(self, field_node: Node, class_name: str):
        self.field_node: Node = field_node
        self.class_name: str = class_name
        declarators: list[str]
        self.modifiers_str: str = ""
        self.modifiers_list: list[str] = []
        self.type: str
        self.is_abstract: bool
        self.is_final: bool
        self.is_static: bool
        self.is_volatile: bool
        self.marker_annotation: str
        self.signature: str
        
        type_node = field_node.child_by_field_name('type')
        self.type = type_node.text.decode('utf-8') if type_node else "Unknown"
        
        mod_node = None
        for child in field_node.children:
            if child.type == 'modifiers':
                mod_node = child
                break
        if mod_node:
            self.modifiers_str = mod_node.text.decode('utf-8')
            self.modifiers_list = self.modifiers_str.split()
        
        self.access_level = "package-private"
        self.is_final = False
        self.is_static = False
        self.is_abstract = False
        self.is_volatile = False
        self.marker_annotation = ""
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
                case "volatile":
                    self.is_volatile = True
        
        
        # find all variable declarators (catches edge case of int x,y,z;)
        declarators = [child for child in field_node.children if child.type == 'variable_declarator']
        
        if declarators:
            first_decl = declarators[0]
            name_node = first_decl.child_by_field_name('name') # 'name' is the field for the identifier
            self.identifier = name_node.text.decode('utf-8')
        else:
            self.identifier = "Unknown"
            
        self.name = f"{class_name}.{self.identifier}"
        
        self.signature = f"{self.type} {self.identifier}"
        parts = [
            self.marker_annotation,                                                 # @Override
            self.access_level if self.access_level!='package-private' else None,    # public
            "abstract" if self.is_abstract else None,                               # abstract
            "static" if self.is_static else None,                                   # static
            "final" if self.is_final else None,                                     # final
            "volatile" if self.is_volatile else None,                               # volatile
            self.signature,                                                         # void MyMethod<T>()
        ]
        self.signature = " ".join(filter(None, parts))
        
    def __str__(self):
        return str(self.signature)
    __repr__ = __str__
        
    