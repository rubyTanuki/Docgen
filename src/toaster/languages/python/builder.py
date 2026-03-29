import os
from tree_sitter import Parser, Node, Query, QueryCursor

from toaster.languages.python.models import PythonFile, PythonClass, PythonEnum, PythonMethod, PythonField
from toaster.core.registry import MemberRegistry
from toaster.languages.python.queries import DEPENDENCY_QUERY
from toaster.languages.python.language import PYTHON_LANGUAGE

class PythonBuilder:
    def __init__(self, registry: MemberRegistry):
        self.registry = registry
        self._dep_query = Query(PYTHON_LANGUAGE, DEPENDENCY_QUERY)

    def parse_file(self, filepath: str) -> PythonFile:
        with open(filepath, "rb") as f:
            source = f.read()
        return self.parse_source(os.path.basename(filepath), source)

    def parse_source(self, filename: str, source_code: bytes) -> PythonFile:
        parser = Parser()
        parser.language = PYTHON_LANGUAGE
        tree = parser.parse(source_code)
        root_node = tree.root_node

        imports = []
        classes = []
        methods = {}
        fields = {}

        for child in root_node.children:
            if child.type == "import_statement":
                for gc in child.children:
                    if gc.type == "dotted_name":
                        imports.append(gc.text.decode("utf-8"))
            elif child.type == "import_from_statement":
                module_name = ""
                for gc in child.children:
                    if gc.type == "dotted_name" or gc.type == "relative_import":
                        module_name = gc.text.decode("utf-8")
                        break
                imports.append(module_name)
            elif child.type == "class_definition":
                py_class = self.parse_class(child)
                classes.append(py_class)
            elif child.type == "function_definition":
                method = self.parse_method(child, scope="")
                methods[method.umid] = method
            elif child.type == "expression_statement":
                for grandchild in child.children:
                    if grandchild.type == "assignment":
                        field = self.parse_field(grandchild, scope="")
                        fields[field.ucid] = field

        file_obj = PythonFile(
            ufid=filename,
            imports=imports,
            classes=classes,
            methods=methods,
            fields=fields,
            registry=self.registry,
        )
        file_obj.source_path = filename
        
        # Plumb context
        self._plumb_context(file_obj)
        
        return file_obj

    def _plumb_context(self, file_obj: PythonFile):
        """Passes context downward recursively."""
        # Plumb module-level methods
        for method in file_obj.methods.values():
            method.file = file_obj

        for class_obj in file_obj.classes:
            self._plumb_class(class_obj, file_obj, class_obj)

    def _plumb_class(
        self, class_obj: PythonClass, file_obj: PythonFile, parent_class: PythonClass
    ):
        for method in class_obj.methods.values():
            method.file = file_obj
            method.parent_class = parent_class

        for child_class in class_obj.child_classes.values():
            self._plumb_class(child_class, file_obj, child_class)

    def parse_class(self, node: Node, scope: str = "") -> PythonClass:
        name_node = node.child_by_field_name("name")
        identifier = name_node.text.decode("utf-8") if name_node else "unknown"
        ucid = f"{scope}.{identifier}" if scope else identifier

        body_node = node.child_by_field_name("body")
        if body_node:
            signature = (
                node.text[: body_node.start_byte - node.start_byte]
                .decode("utf-8")
                .strip()
            )
            if signature.endswith(":"):
                signature = signature[:-1].strip()
        else:
            signature = node.text.decode("utf-8").strip()

        body_text = body_node.text.decode("utf-8") if body_node else ""

        instance = PythonClass(
            ucid=ucid,
            signature=signature,
            body=body_text,
            start_line=node.start_point[0],
            node=node,
            registry=self.registry
        )
        self.registry.add_class(instance)

        if body_node:
            for child in body_node.children:
                ct = child.type
                if ct == "function_definition":
                    method = self.parse_method(child, instance.ucid)
                    instance.methods[method.umid] = method
                    
                    # Search for instance variables (self.X) inside the method
                    self._extract_self_fields(child, instance)
                    
                elif ct == "class_definition":
                    child_class = self.parse_class(child, instance.ucid)
                    instance.child_classes[child_class.ucid] = child_class
                elif ct == "expression_statement":
                    # Potentially a class attribute (field)
                    for grandchild in child.children:
                        if grandchild.type == "assignment":
                            field = self.parse_field(grandchild, instance.ucid)
                            instance.fields[field.ucid] = field

        return instance

    def _extract_self_fields(self, method_node: Node, class_instance: PythonClass):
        # Simple traversal to find self.X = ...
        body = method_node.child_by_field_name("body")
        if not body:
            return

        def find_assignments(n):
            if n.type == "assignment":
                left = n.child_by_field_name("left")
                if left and left.type == "attribute":
                    obj = left.child_by_field_name("object")
                    attr = left.child_by_field_name("attribute")
                    if obj and obj.text.decode('utf-8') == "self" and attr:
                        field_name = attr.text.decode('utf-8')
                        
                        field_type = "var"
                        type_node = n.child_by_field_name("type")
                        if type_node:
                            field_type = type_node.text.decode('utf-8').strip()

                        ucid = f"{class_instance.ucid}.{field_name}"
                        if ucid not in class_instance.fields:
                            field = PythonField(
                                ucid=ucid,
                                name=field_name,
                                signature=n.text.decode('utf-8').strip(),
                                field_type=field_type
                            )
                            class_instance.fields[ucid] = field
                        elif field_type != "var" and class_instance.fields[ucid].field_type == "var":
                            class_instance.fields[ucid].field_type = field_type
                            class_instance.fields[ucid].signature = n.text.decode('utf-8').strip()

            for child in n.children:
                find_assignments(child)
        
        find_assignments(body)

    def parse_method(self, node: Node, scope: str) -> PythonMethod:
        name_node = node.child_by_field_name("name")
        identifier = name_node.text.decode("utf-8") if name_node else "unknown"

        # Parameters extraction
        params_node = node.child_by_field_name("parameters")
        params_full = []
        if params_node:
            for child in params_node.children:
                if child.type in (
                    "identifier",
                    "typed_parameter",
                    "default_parameter",
                    "typed_default_parameter",
                    "list_splat_pattern",
                    "dictionary_splat_pattern",
                    "slash",
                    "star",
                ):
                    params_full.append(child.text.decode("utf-8"))

        # Return type handling
        return_type_node = node.child_by_field_name("return_type")
        return_type = (
            return_type_node.text.decode("utf-8").strip()
            if return_type_node
            else "var"
        )

        scoped_identifier = f"{scope}.{identifier}" if scope else identifier
        umid = (
            f"{scope}#{identifier}({','.join(params_full)})"
            if scope
            else f"{identifier}({','.join(params_full)})"
        )

        body_node = node.child_by_field_name("body")
        dependency_names = []
        if body_node:
            signature = (
                node.text[: body_node.start_byte - node.start_byte]
                .decode("utf-8")
                .strip()
            )
            if signature.endswith(":"):
                signature = signature[:-1].strip()
            
            # Extract dependencies
            cursor = QueryCursor(self._dep_query)
            captures = cursor.captures(body_node)
            
            if "dependencies" in captures:
                for d_node in captures["dependencies"]:
                    # d_node is a 'call'
                    func_node = d_node.child_by_field_name('function')
                    if not func_node: continue
                    
                    target_name_node = None
                    if func_node.type == 'attribute':
                        target_name_node = func_node.child_by_field_name('attribute')
                    elif func_node.type == 'identifier':
                        target_name_node = func_node
                    
                    if not target_name_node: continue
                    
                    # Count arguments properly
                    args_node = d_node.child_by_field_name('arguments')
                    arity = 0
                    if args_node:
                        arity = len([c for c in args_node.children if c.is_named])
                    
                    dependency_names.append((
                        target_name_node.text.decode('utf-8'),
                        arity
                    ))
        else:
            signature = node.text.decode("utf-8").strip()

        body = body_node.text.decode("utf-8") if body_node else ""

        instance = PythonMethod(
            identifier=identifier,
            scoped_identifier=scoped_identifier,
            return_type=return_type,
            umid=umid,
            signature=signature,
            body=body,
            dependency_names=dependency_names,
            start_line=node.start_point[0],
            parameters=params_full,
            node=node,
            registry=self.registry
        )
        self.registry.add_method(instance)
        
        return instance

    def parse_field(self, node: Node, scope: str = "") -> PythonField:
        name_node = node.child_by_field_name('left')
        name = name_node.text.decode('utf-8') if name_node else "unknown"
        
        type_node = node.child_by_field_name('type')
        field_type = type_node.text.decode('utf-8').strip() if type_node else "var"
        
        ucid = f"{scope}.{name}" if scope else name
        signature = node.text.decode('utf-8').strip()
        
        return PythonField(
            ucid=ucid,
            name=name,
            signature=signature,
            field_type=field_type
        )
