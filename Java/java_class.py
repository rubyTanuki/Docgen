from tree_sitter import Tree, Query, QueryCursor

from language import JAVA_LANGUAGE
from queries import CLASS_QUERY
from java_method import Method
from java_field import Field

class Class:
    ACCESS_MODIFIERS = {"public", "protected", "private"}
    def __init__(self, tree: Tree, package: str):
        # extract class node
        self.access_level = "protected"
        self.is_final = False
        self.is_abstract = False
        self.is_static = False
        
        query = Query(JAVA_LANGUAGE, CLASS_QUERY)
        query_cursor = QueryCursor(query)
        captures = query_cursor.captures(tree)
        
        body_node = captures["body"][0]
        self.body = body_node.text.decode('utf-8')
        self.identifier = captures["identifier"][0].text.decode('utf-8')
        self.name = package + "." + self.identifier if package is not "" else self.identifier
        self.modifiers = captures["modifiers"][0].text.decode('utf-8') + " " if "modifiers" in captures else ""
        
        
        # extract modifiers
        for mod in self.modifiers.split(" "):
            if mod in self.ACCESS_MODIFIERS:
                self.access_level = mod
            if mod == "final":
                self.is_final = True
            if mod == "abstract":
                self.is_abstract = True
            if mod == "static":
                self.is_static = True
        
        # build final class signature string
        self.signature = f"{self.modifiers}class {self.identifier}"
        
        # extract and build methods and fields
        self.methods = {}
        self.fields = {}
        for child in body_node.children:
            if child.type == "method_declaration":
                method = Method(child, self.name)
                self.methods[method.identifier] = method
            if child.type == "field_declaration":
                field = Field(child, self.name)
                self.fields[field.identifier] = field
        
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
        
    