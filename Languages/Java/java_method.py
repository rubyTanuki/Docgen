from tree_sitter import Node, Query, QueryCursor

from queries import DEPENDENCY_QUERY
from language import JAVA_LANGUAGE

from member_registry import MemberRegistry

from Languages.Agnostic.Method import Method

class JavaMethod(Method):
    
    _DEP_QUERY = Query(JAVA_LANGUAGE, DEPENDENCY_QUERY)
    ACCESS_MODIFIERS = {"public", "protected", "private"}
    def __init__(self, method_node: Node, class_name: str):
        
        # init class variables
        self.method_node: Node = method_node
        self.class_name: str = class_name
        self.dependencies: list[str] = []
        self.identifier: str
        self.name: str
        self.return_type: str
        self.modifiers_str: str
        self.modifiers_list: list[str]
        self.is_abstract: bool
        self.is_final: bool
        self.is_static: bool
        self.is_synchronized: bool
        self.marker_annotation: str
        self.type_parameters: list[str]
        self.parameters: list[str]
        self.body_node: Node
        self.body: str
        self.signature: str
        self.description: str
        self.context_needed: bool = False
        
        # identifier
        identifier_node = method_node.child_by_field_name('name')
        self.identifier: str = identifier_node.text.decode('utf-8') if identifier_node else "<init>"
        self.name = f"{class_name}.{self.identifier}"
        
        # return type
        type_node = method_node.child_by_field_name('type')
        if type_node:
            self.return_type = type_node.text.decode('utf-8')
        elif method_node.type == 'constructor_declaration':
            self.return_type = self.class_name
        else:
            self.return_type = "void"
        
        # modifiers and type parameters
        self.modifiers_str = ""
        self.type_parameters = []
        for child in method_node.children:
            if child.type == 'modifiers':
                self.modifiers_str = child.text.decode('utf-8')
                self.modifiers_list = self.modifiers_str.split()
                break
            if child.type == 'type_parameters':
                for grandchild in child.children:
                    if grandchild.type == "type_parameter":
                        self.type_parameters.append(grandchild.text.decode('utf-8'))
        
        # parse modifiers
        self.access_level = "package-private"
        self.is_final = False
        self.is_static = False
        self.is_abstract = False
        self.is_synchronized = False
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
                case "synchronized":
                    self.is_synchronized = True
        
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
        self.signature = f"{self.return_type} {self.identifier}"
        if self.type_parameters:
            self.signature += f"<{', '.join(self.type_parameters)}>"
        self.signature += f"({param_str})"
        parts = [
            self.marker_annotation,                                                 # @Override
            self.access_level if self.access_level!='package-private' else None,    # public
            "abstract" if self.is_abstract else None,                               # abstract
            "static" if self.is_static else None,                                   # static
            "final" if self.is_final else None,                                     # final
            "synchronized" if self.is_synchronized else None,                       # synchronized
            self.signature,                                                         # void MyMethod<T>()
        ]
        self.signature = " ".join(filter(None, parts))
        
        MemberRegistry.add_method(self)
    
    def resolve_dependencies(self, imports: list[str] = []) -> None:
        if not self.body_node: 
            return
        
        query_cursor = QueryCursor(self._DEP_QUERY)
        captures = query_cursor.captures(self.body_node)
        
        # Use a set to avoid duplicates (e.g., calling println 5 times)
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
            # if MemberRegistry.methods_by_name[name] != []:
            #     print(f"FAILED TO RESOLVE DEPENDENCY: defaulting to all {name} methods in registry")
            # else:
            #     print(f"FAILED TO RESOLVE DEPENDENCY: no {name} methods in registry (check imports)")
    
    def __str__(self) -> str:
        return self.signature.strip()
    __repr__ = __str__
        
    