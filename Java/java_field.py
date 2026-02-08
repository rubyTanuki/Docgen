from tree_sitter import Node, Query, QueryCursor

from queries import FIELD_QUERY
from language import JAVA_LANGUAGE

class Field:
    ACCESS_MODIFIERS = {"public", "protected", "private"}
    def __init__(self, field_node: Node, class_name: str):
        self.class_name = class_name
        
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
        else:
            self.modifiers_str = ""
            self.modifiers_list = []
        
        
        # find all variable declarators (catches edge case of int x,y,z;)
        declarators = [child for child in field_node.children if child.type == 'variable_declarator']
        
        if declarators:
            first_decl = declarators[0]
            name_node = first_decl.child_by_field_name('name') # 'name' is the field for the identifier
            self.identifier = name_node.text.decode('utf-8')
        else:
            self.identifier = "Unknown"
            
        self.name = f"{class_name}.{self.identifier}"
        self._parse_modifiers()
        
        self.signature = f"{self.modifiers_str} {self.type} {self.identifier}"
            
    def _parse_modifiers(self):
        ACCESS_MODIFIERS = {"public", "protected", "private"}
        self.access_level = "package-private" # Default
        self.is_final = False
        self.is_static = False
        
        for mod in self.modifiers_list:
            if mod in ACCESS_MODIFIERS:
                self.access_level = mod
            if mod == "final":
                self.is_final = True
            if mod == "static":
                self.is_static = True
        
    def __str__(self):
        return str(self.signature)
    __repr__ = __str__
        
    