from tree_sitter import Node, Query, QueryCursor

from queries import DEPENDENCY_QUERY
from language import JAVA_LANGUAGE

from member_registry import MemberRegistry

class Method:
    
    _DEP_QUERY = Query(JAVA_LANGUAGE, DEPENDENCY_QUERY)
    ACCESS_MODIFIERS = {"public", "protected", "private"}
    def __init__(self, method_node: Node, class_name: str):
        self.method_node = method_node
        self.class_name = class_name
        self.dependencies = []
        
        # identifier
        name_node = method_node.child_by_field_name('name')
        self.identifier = name_node.text.decode('utf-8') if name_node else "<init>"
        self.name = f"{class_name}.{self.identifier}"
        
        # return type
        type_node = method_node.child_by_field_name('type')
        if type_node:
            self.return_type = type_node.text.decode('utf-8')
        elif method_node.type == 'constructor_declaration':
            self.return_type = self.class_name
        else:
            self.return_type = "void"
        
        # modifiers
        mod_node = None
        for child in method_node.children:
            if child.type == 'modifiers':
                mod_node = child
                break
        self.modifiers_str = mod_node.text.decode('utf-8') if mod_node else ""
        self._parse_modifiers(self.modifiers_str)
        
        
        # parameters
        params_node = method_node.child_by_field_name('parameters')
        self.parameters = []
        if params_node:
            for child in params_node.children:
                if child.type == 'formal_parameter':
                    self.parameters.append(child.text.decode('utf-8'))
                elif child.type == 'spread_parameter': # Java varargs (String... args)
                    self.parameters.append(child.text.decode('utf-8'))
        
        # body
        body_node = method_node.child_by_field_name('body')
        if body_node:
            self.body = body_node.text.decode('utf-8')
        else:
            self.body = "" # Abstract method or Interface
            
            
        # signature
        param_str = ", ".join(self.parameters)
        self.signature = (f"{self.modifiers_str} {self.return_type} {self.identifier}({param_str})")
        
        MemberRegistry.add_method(self)
    
    def _parse_modifiers(self, mod_string):
        self.access_level = "package-private"
        self.is_final = False
        self.is_static = False
        self.is_abstract = False
        
        for mod in mod_string.split():
            if mod in self.ACCESS_MODIFIERS:
                self.access_level = mod
            if mod == "final":
                self.is_final = True
            if mod == "abstract":
                self.is_abstract = True
            if mod == "static":
                self.is_static = True
        
    def resolve_dependencies(self, imports: list[str] = []):
        # query = Query(JAVA_LANGUAGE, DEPENDENCY_QUERY)
        # query_cursor = QueryCursor(query)
        # captures = query_cursor.captures(self.method_node)
        # dependency_names = [c.text.decode('utf-8') for c in captures["dependencies"]] if "dependencies" in captures else []
        body_node = self.method_node.child_by_field_name('body')
        if not body_node: 
            return
        
        query_cursor = QueryCursor(self._DEP_QUERY)
        captures = query_cursor.captures(body_node)
        
        # Use a set to avoid duplicates (e.g., calling println 5 times)
        dependency_names = set()
        if "dependencies" in captures:
            for node in captures["dependencies"]:
                dependency_names.add(node.text.decode('utf-8'))
        
        if not dependency_names:
            return

        # print("DEPENDENCIES: " + str(dependency_names))
        
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
            for dependency in MemberRegistry.methods_by_name[name]:
                self.dependencies.append(dependency)
            # if MemberRegistry.methods_by_name[name] != []:
            #     print(f"FAILED TO RESOLVE DEPENDENCY: defaulting to all {name} methods in registry")
            # else:
            #     print(f"FAILED TO RESOLVE DEPENDENCY: no {name} methods in registry (check imports)")
    
    def get_tuple(self) -> (str, str):
        return (self.class_name, self.identifier)
    
    def __str__(self) -> str:
        return self.signature.strip()
    __repr__ = __str__
        
    