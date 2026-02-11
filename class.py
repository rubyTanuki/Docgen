from tree_sitter import Tree, Query, QueryCursor

from collections import defaultdict

class Class:
    def __init__(self, tree: Tree, package: str):
        pass
            
    def get_methods(self) -> list[Method]:
        return []
    
    def get_fields(self):
        return []
    
    def get_members(self):
        return self.get_fields() + self.get_methods()
    
    def __iter__(self):
        return iter(self.methods.values())
    
    def __getitem__(self, key) -> Method:
        return self.methods[key]
    
    def __str__(self):
        return "\n" + self.signature + "\n\t" + "\n\t".join([str(member) for member in self.get_members()]) + "\n"
    __repr__ = __str__
        
    