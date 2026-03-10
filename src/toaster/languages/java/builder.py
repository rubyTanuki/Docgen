import os
from tree_sitter import Parser, Node, Query, QueryCursor

from toaster.languages.java.models import JavaFile, JavaClass, JavaEnum, JavaMethod, JavaField
from toaster.core.registry import MemberRegistry
from toaster.languages.java.queries import DEPENDENCY_QUERY
from toaster.languages.java.language import JAVA_LANGUAGE

class JavaBuilder:
    def __init__(self, registry: MemberRegistry):
        self.registry = registry
        self._dep_query = Query(JAVA_LANGUAGE, DEPENDENCY_QUERY)

    def parse_file(self, filepath: str) -> JavaFile:
        with open(filepath, "rb") as f:
            source = f.read()
        return self.parse_source(os.path.basename(filepath), source)

    def parse_source(self, filename: str, source_code: bytes) -> JavaFile:
        parser = Parser()
        parser.language = JAVA_LANGUAGE
        tree = parser.parse(source_code)
        root_node = tree.root_node
        
        scope = ""
        imports = []
        classes = []

        for child in root_node.children:
            if child.type == "package_declaration":
                for grandchild in child.children:
                    if grandchild.type in {"scoped_identifier", "identifier"}:
                        scope = grandchild.text.decode('utf-8')
                        break
            elif child.type == "import_declaration":
                for grandchild in child.children:
                    if grandchild.type in {"scoped_identifier", "identifier"}:
                        imports.append(grandchild.text.decode('utf-8'))
            elif child.type == "class_declaration" or child.type == "interface_declaration":
                java_class = self.parse_class(child, scope)
                classes.append(java_class)
            elif child.type == "enum_declaration":
                java_enum = self.parse_enum(child, scope)
                classes.append(java_enum)

        # Create file object
        file_obj = JavaFile(
            ufid=filename,
            imports=imports,
            classes=classes,
            registry=self.registry
        )

        # Plumb the context linearly now that the file is built
        self._plumb_context(file_obj)
        
        return file_obj

    def _plumb_context(self, file_obj: JavaFile):
        """Passes context downward recursively."""
        for class_obj in file_obj.classes:
            self._plumb_class(class_obj, file_obj, class_obj)
            
    def _plumb_class(self, class_obj: JavaClass, file_obj: JavaFile, parent_class: JavaClass):
        for method in class_obj.methods.values():
            method.file = file_obj
            method.parent_class = parent_class
            
        for child_class in class_obj.child_classes.values():
            self._plumb_class(child_class, file_obj, child_class)

    def parse_class(self, node: Node, scope: str = "") -> JavaClass:
        identifier: str = ""
        superclass: str = ""
        modifiers: list[str] = []
        interfaces: list[str] = []
        type_params: list[str] = []
        body_node = None
        
        identifier_node = node.child_by_field_name('name')
        if identifier_node:
            identifier = identifier_node.text.decode('utf-8')
        
        ucid = f"{scope}.{identifier}" if scope else identifier

        for child in node.children:
            child_type = child.type
            if child_type == "modifiers":
                for mod_node in child.children:
                    if mod_node.type not in ['line_comment', 'block_comment', 'annotation', 'marker_annotation']:
                        modifiers.append(mod_node.text.decode('utf-8'))
            elif child_type == "type_parameters":
                type_params = child.text.decode('utf-8')
            elif child_type == "superclass":
                for gc in child.children:
                    if "type" in gc.type:
                        superclass = gc.text.decode('utf-8')
            elif child_type == "super_interfaces":
                type_list = child.child_by_field_name('interfaces')
                if type_list:
                    interfaces = [c.text.decode('utf-8') for c in type_list.children if "type" in c.type]
            elif child_type == "class_body" or child_type == "interface_body":
                body_node = child

        access = "package-private"
        is_interface = node.type == "interface_declaration"
        other_mods = []
        
        for mod in modifiers:
            if mod in JavaClass.ACCESS_MODIFIERS:
                access = mod
            else:
                other_mods.append(mod)
        
        generics_str = type_params if type_params else ""
        
        sig_parts = [access] + other_mods + ["class" if not is_interface else "interface", identifier + generics_str]
        
        if 'superclass' in sig_parts:
            sig_parts.remove('superclass')
        
        if superclass:
            sig_parts.append(f"extends {superclass}")
        if interfaces:
            sig_parts.append(f"implements {', '.join(interfaces)}")
            
        signature = " ".join(filter(None, sig_parts))
        final_body = body_node.text.decode('utf-8') if body_node else ""

        instance = JavaClass(
            ucid=ucid,
            signature=signature,
            body=final_body,
            start_line=node.start_point[0],
            node=node,
            registry=self.registry
        )
        self.registry.add_class(instance)

        if body_node:
            for child in body_node.children:
                ct = child.type
                if ct in ("method_declaration", "constructor_declaration"):
                    method = self.parse_method(child, instance.ucid)
                    instance.methods[method.umid] = method
                    
                elif ct == "field_declaration":
                    field = self.parse_field(child, instance.ucid)
                    instance.fields[field.ucid] = field
                    
                elif ct == "class_declaration" or ct == "interface_declaration":
                    child_class = self.parse_class(child, instance.ucid)
                    instance.child_classes[child_class.ucid] = child_class
                    self.registry.add_class(child_class)
                    
                elif ct == "enum_declaration":
                    child_class = self.parse_enum(child, instance.ucid)
                    instance.child_classes[child_class.ucid] = child_class
                    self.registry.add_class(child_class)

        return instance

    def parse_enum(self, node: Node, scope: str = "") -> JavaEnum:
        identifier: str = ""
        modifiers: list[str] = []
        interfaces: list[str] = []
        body_node = None
        
        name_node = node.child_by_field_name('name')
        if name_node:
            identifier = name_node.text.decode('utf-8')

        ucid = f"{scope}.{identifier}" if scope else identifier

        for child in node.children:
            child_type = child.type
            if child_type == "modifiers":
                modifiers = child.text.decode('utf-8').split()
            elif child_type == "super_interfaces":
                type_list = child.child_by_field_name('interfaces')
                if type_list:
                    interfaces = [c.text.decode('utf-8') for c in type_list.children if "type" in c.type]
                else:
                    interfaces = [c.text.decode('utf-8') for c in child.children if "type" in c.type]
            elif child_type == "enum_body":
                body_node = child

        access = "package-private"
        other_mods = []
        for mod in modifiers:
            if mod in JavaClass.ACCESS_MODIFIERS:
                access = mod
            else:
                other_mods.append(mod)

        sig_parts = [access] + other_mods + ["enum", identifier]
        if interfaces:
            sig_parts.append(f"implements {', '.join(interfaces)}")
        final_signature = " ".join(filter(None, sig_parts))
        
        final_body = body_node.text.decode('utf-8') if body_node else ""
        
        instance = JavaEnum(
            ucid=ucid, 
            signature=final_signature, 
            body=final_body, 
            start_line=node.start_point[0],
            node=node, 
            registry=self.registry
        )
        self.registry.add_class(instance)

        if body_node:
            for child in body_node.children:
                ct = child.type
                if ct == "enum_constant":
                    const_name = child.child_by_field_name('name').text.decode('utf-8')
                    args_node = child.child_by_field_name('arguments')
                    if args_node:
                        const_name += args_node.text.decode('utf-8')
                    instance.constants.append(const_name)

                elif ct in ("method_declaration", "constructor_declaration"):
                    method = self.parse_method(child, instance.ucid)
                    instance.methods[method.umid] = method
                    
                elif ct == "field_declaration":
                    field = self.parse_field(child, instance.ucid)
                    instance.fields[field.ucid] = field

        return instance

    def parse_method(self, node: Node, scope: str) -> JavaMethod:
        start_line = node.start_point[0]
        identifier = "<init>"
        return_type = "void"
        
        name_node = node.child_by_field_name('name')
        if name_node:
            identifier = name_node.text.decode('utf-8')
            
        if node.type != 'constructor_declaration':
            type_node = node.child_by_field_name('type')
            if type_node:
                return_type = type_node.text.decode('utf-8')
            elif node.child_by_field_name('dimensions'):
                return_type = "void"
                
        params_full = []
        params_node = node.child_by_field_name('parameters')
        if params_node:
            for child in params_node.children:
                if child.type in ("formal_parameter", "spread_parameter"):
                    params_full.append(child.text.decode('utf-8'))
        
        umid = f"{scope}#{identifier}({','.join(params_full)})"
        scoped_identifier = f"{scope}.{identifier}"
        
        modifiers_str = ""
        throws_clause = ""
        type_params = ""
        
        for child in node.children:
            ct = child.type
            if ct == "modifiers":
                modifiers_str = child.text.decode('utf-8').strip()
            elif ct == "type_parameters":
                type_params = child.text.decode('utf-8').strip()
            elif ct == "throws":
                throws_clause = child.text.decode('utf-8').strip()
                
        if return_type == "void" and node.type == 'constructor_declaration':
            return_type = "<constructor>"
            sig_parts = [modifiers_str, type_params, identifier]
        else:
            sig_parts = [modifiers_str, type_params, return_type, identifier]
            
        base_sig = " ".join(filter(None, sig_parts))
        full_sig_str = f"{base_sig}({', '.join(params_full)})"
        
        if throws_clause:
            full_sig_str += f" {throws_clause}"
        
        body = ""
        dependency_names = []

        body_node = node.child_by_field_name('body')
        if body_node:
            body = body_node.text.decode('utf-8')
            
            cursor = QueryCursor(self._dep_query)
            captures = cursor.captures(body_node)
            
            if "dependencies" in captures:
                for d_node in captures["dependencies"]:
                    dependency_names.append((
                        d_node.text.decode('utf-8'), 
                        d_node.child_by_field_name('name').text.decode('utf-8')
                    ))
                            
        instance = JavaMethod(
            identifier=identifier, 
            scoped_identifier=scoped_identifier,
            return_type=return_type, 
            umid=umid, 
            signature=full_sig_str, 
            body=body, 
            dependency_names=dependency_names, 
            start_line=start_line, 
            parameters=params_full, 
            node=node, 
            registry=self.registry,
            file=None,
            parent_class=None
        )
        self.registry.add_method(instance)
        return instance

    def parse_field(self, node: Node, scope: str = "") -> JavaField:
        type_text: str = ""
        modifiers: list[str] = []
        identifier: str = "Unknown"
        value: str = ""
        
        type_node = node.child_by_field_name('type')
        if type_node:
            type_text = type_node.text.decode('utf-8')

        for child in node.children:
            child_type = child.type
            if child_type == "modifiers":
                modifiers = child.text.decode('utf-8').split()
            elif child_type == "variable_declarator":
                name_node = child.child_by_field_name('name')
                if name_node:
                    identifier = name_node.text.decode('utf-8')
                value_node = child.child_by_field_name('value')
                if value_node:
                    value = value_node.text.decode('utf-8')
                break

        ucid = f"{scope}.{identifier}" if scope else identifier

        access = "package-private"
        other_mods = []
        for mod in modifiers:
            if mod in JavaClass.ACCESS_MODIFIERS:
                access = mod
            else:
                other_mods.append(mod)

        sig_parts = [access] + other_mods + [type_text, identifier]
        signature = " ".join(filter(None, sig_parts))
        
        if value:
            signature += f" = {value}"

        return JavaField(
            ucid=ucid, 
            name=identifier, 
            signature=signature, 
            field_type=type_text
        )
