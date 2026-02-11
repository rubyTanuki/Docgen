from tree_sitter import Node, Query, QueryCursor


class Method:
    
    def __init__(self, method_node: Node, class_name: str):
        self.class_name: str = class_name
        self.dependencies: list[str] = []
        self.identifier: str
        self.name: str = f"{class_name}.{self.identifier}"
        self.return_type: str
        self.modifiers_str: str
        self._parse_modifiers(self.modifiers_str)
        self.parameters: list[str]
        self.body: str
        self.signature: str
        
    def resolve_dependencies(self, imports: list[str] = []):
        pass
    
    def __str__(self) -> str:
        return self.signature.strip()
    __repr__ = __str__
        
    