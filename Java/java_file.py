from tree_sitter import Tree, Query, QueryCursor, Language, Parser

from language import JAVA_LANGUAGE
from queries import PACKAGE_QUERY
from java_method import Method
from java_class import Class
from member_registry import MemberRegistry

class File:
    def __init__(self, file: str):
        parser = Parser()
        parser.language = JAVA_LANGUAGE
        tree = parser.parse(file)
        query = Query(JAVA_LANGUAGE, "(class_declaration) @classes")
        query_cursor = QueryCursor(query)
        class_captures = query_cursor.captures(tree.root_node)
        
        
        query = Query(JAVA_LANGUAGE, PACKAGE_QUERY)
        query_cursor = QueryCursor(query)
        package_captures = query_cursor.captures(tree.root_node)
        self.package = package_captures["package"][0].text.decode('utf-8') if "package" in package_captures else ""
        print("PACKAGE: " + self.package)
        # inits classes, methods, and fields
        self.classes = [Class(class_tree, self.package) for class_tree in class_captures["classes"]]
        
        self.imports = [i.text.decode('utf-8') for i in package_captures["imports"]]
        print(self.classes)
        print("ALL METHODS: " + str(MemberRegistry.methods.keys()))
        for c in self.classes:
            for m in c:
                m.resolve_dependencies(self.imports)
        
        
        

