import os
from tree_sitter import Parser, Node, Query, QueryCursor

from toaster.languages.csharp.models import CSharpFile, CSharpClass, CSharpEnum, CSharpMethod, CSharpField
from toaster.core.registry import MemberRegistry
from toaster.languages.csharp.queries import DEPENDENCY_QUERY
from toaster.languages.csharp.language import CSHARP_LANGUAGE

class CSharpBuilder:
    def __init__(self, registry: MemberRegistry):
        self.registry = registry
        self._dep_query = Query(CSHARP_LANGUAGE, DEPENDENCY_QUERY)

    def parse_file(self, filepath: str) -> CSharpFile:
        with open(filepath, "rb") as f:
            source = f.read()
        return self.parse_source(os.path.basename(filepath), source)

    def parse_source(self, filename: str, source_code: bytes) -> CSharpFile:
        parser = Parser()
        parser.language = CSHARP_LANGUAGE
        tree = parser.parse(source_code)
        root_node = tree.root_node
        
        scope = ""
        imports = []
        classes = []

        def search_root(node: Node):
            nonlocal scope
            if node.type == "using_directive":
                # handle "using System;"
                for child in node.children:
                    if child.type in {"identifier", "qualified_name"}:
                        imports.append(child.text.decode('utf-8'))
                        
            elif node.type in {"namespace_declaration", "file_scoped_namespace_declaration"}:
                name_node = node.child_by_field_name('name')
                if name_node:
                    scope = name_node.text.decode('utf-8')
                # if regular namespace, class declarations are inside its declaration_list
                # if file_scoped, they are normally siblings, but grammar might nest them
                # we just traverse children
                if node.type == "namespace_declaration":
                    body = node.child_by_field_name('body')
                    if body:
                        for child in body.children:
                            search_root(child)
                else:
                    for child in node.children:
                        if child.type not in {"namespace_declaration", "file_scoped_namespace_declaration", "using_directive"}:
                            search_root(child)
            
            elif node.type in {"class_declaration", "interface_declaration", "record_declaration", "struct_declaration"}:
                csharp_class = self.parse_class(node, scope)
                classes.append(csharp_class)
            elif node.type == "enum_declaration":
                csharp_enum = self.parse_enum(node, scope)
                classes.append(csharp_enum)
            else:
                for child in node.children:
                    # just basic recursion if we haven't hit namespace/class
                    if node.type == "compilation_unit":
                        search_root(child)

        search_root(root_node)

        file_obj = CSharpFile(
            ufid=filename,
            imports=imports,
            classes=classes,
            registry=self.registry
        )

        self._plumb_context(file_obj)
        return file_obj

    def _plumb_context(self, file_obj: CSharpFile):
        """Passes context downward recursively."""
        for class_obj in file_obj.classes:
            self._plumb_class(class_obj, file_obj, class_obj)
            
    def _plumb_class(self, class_obj: CSharpClass, file_obj: CSharpFile, parent_class: CSharpClass):
        for method in class_obj.methods.values():
            method.file = file_obj
            method.parent_class = parent_class
            
        for child_class in class_obj.child_classes.values():
            self._plumb_class(child_class, file_obj, child_class)

    def parse_class(self, node: Node, scope: str = "") -> CSharpClass:
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
            if child_type == "modifier":
                modifiers.append(child.text.decode('utf-8'))
            elif child_type == "type_parameter_list":
                type_params = child.text.decode('utf-8')
            elif child_type == "base_list":
                # C# uses base_list for both base class and interfaces " : BaseClass, IInterface"
                types = [c.text.decode('utf-8') for c in child.children if c.type in {"identifier", "generic_name", "qualified_name"}]
                if types:
                    superclass = types[0] # assume first is class
                    interfaces = types[1:]
            elif child_type in {"declaration_list", "record_base"}:
                body_node = child

        access = "internal" # default in C#
        other_mods = []
        
        modifier_nodes = [m for child in node.children if child.type == "modifier" for m in [child.text.decode('utf-8')]]
        modifiers = modifier_nodes

        for mod in modifiers:
            if mod in CSharpClass.ACCESS_MODIFIERS:
                access = mod
            else:
                other_mods.append(mod)
        
        generics_str = type_params if type_params else ""
        
        # Determine keyword
        class_keyword = "class"
        if node.type == "interface_declaration": class_keyword = "interface"
        if node.type == "record_declaration": class_keyword = "record"
        if node.type == "struct_declaration": class_keyword = "struct"

        sig_parts = [access] + other_mods + [class_keyword, identifier + generics_str]
        
        if superclass or interfaces:
            base_str = " : " + ", ".join(filter(None, [superclass] + interfaces))
            sig_parts.append(base_str)
            
        signature = " ".join(filter(None, sig_parts))
        final_body = body_node.text.decode('utf-8') if body_node else "{}"

        instance = CSharpClass(
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
                if ct in {"method_declaration", "constructor_declaration", "local_function_statement"}:
                    method = self.parse_method(child, instance.ucid)
                    instance.methods[method.umid] = method
                elif ct == "property_declaration":
                    # For RAG context, properties are basically methods. We will parse them as methods.
                    method = self.parse_method(child, instance.ucid)
                    instance.methods[method.umid] = method
                elif ct == "field_declaration":
                    field = self.parse_field(child, instance.ucid)
                    instance.fields[field.ucid] = field
                elif ct in {"class_declaration", "interface_declaration", "record_declaration", "struct_declaration"}:
                    child_class = self.parse_class(child, instance.ucid)
                    instance.child_classes[child_class.ucid] = child_class
                    self.registry.add_class(child_class)
                elif ct == "enum_declaration":
                    child_class = self.parse_enum(child, instance.ucid)
                    instance.child_classes[child_class.ucid] = child_class
                    self.registry.add_class(child_class)

        # Handle record primary constructors as properties
        if node.type == "record_declaration":
            param_list = node.child_by_field_name("parameters")
            if param_list:
                # We can mock these as fields/properties.
                pass

        return instance

    def parse_enum(self, node: Node, scope: str = "") -> CSharpEnum:
        identifier: str = ""
        modifiers: list[str] = []
        body_node = None
        
        name_node = node.child_by_field_name('name')
        if name_node:
            identifier = name_node.text.decode('utf-8')

        ucid = f"{scope}.{identifier}" if scope else identifier

        for child in node.children:
            child_type = child.type
            if child_type == "modifier":
                modifiers.append(child.text.decode('utf-8'))
            elif child_type == "enum_member_declaration_list":
                body_node = child

        access = "internal"
        other_mods = []
        for mod in modifiers:
            if mod in CSharpClass.ACCESS_MODIFIERS:
                access = mod
            else:
                other_mods.append(mod)

        sig_parts = [access] + other_mods + ["enum", identifier]
        final_signature = " ".join(filter(None, sig_parts))
        
        final_body = body_node.text.decode('utf-8') if body_node else "{}"
        
        instance = CSharpEnum(
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
                if ct == "enum_member_declaration":
                    const_name = child.child_by_field_name('name').text.decode('utf-8')
                    instance.constants.append(const_name)

        return instance

    def parse_method(self, node: Node, scope: str) -> CSharpMethod:
        start_line = node.start_point[0]
        identifier = "<init>"
        return_type = "void"
        
        name_node = node.child_by_field_name('name')
        if name_node:
            identifier = name_node.text.decode('utf-8')
            
        if node.type not in {'constructor_declaration'}:
            type_node = node.child_by_field_name('type')
            if type_node:
                return_type = type_node.text.decode('utf-8')
                
        params_full = []
        params_node = node.child_by_field_name('parameters')
        if params_node:
            for child in params_node.children:
                if child.type == "parameter":
                    params_full.append(child.text.decode('utf-8'))
        
        umid = f"{scope}#{identifier}({','.join(params_full)})"
        scoped_identifier = f"{scope}.{identifier}"
        
        modifiers = []
        type_params = ""
        
        for child in node.children:
            ct = child.type
            if ct == "modifier":
                modifiers.append(child.text.decode('utf-8'))
            elif ct == "type_parameter_list":
                type_params = child.text.decode('utf-8')
                
        modifiers_str = " ".join(modifiers)
                
        if node.type == 'constructor_declaration':
            return_type = "<constructor>"
            sig_parts = [modifiers_str, type_params, identifier]
        elif node.type == 'property_declaration':
            sig_parts = [modifiers_str, type_params, return_type, identifier]
        else:
            sig_parts = [modifiers_str, type_params, return_type, identifier]
            
        base_sig = " ".join(filter(None, [part for part in sig_parts if part]))
        
        if node.type == 'property_declaration':
            full_sig_str = f"{base_sig} {{ get; set; }}"
        else:
            full_sig_str = f"{base_sig}({', '.join(params_full)})"
        
        body = ""
        dependency_names = []

        body_node = node.child_by_field_name('body')
        if not body_node:
            # Check for expression body "=>"
            # In tree-sitter C# it might be an arrow_expression_clause
            for child in node.children:
                if child.type == "arrow_expression_clause":
                    body_node = child
                    break
            # Or for properties, an accessor_list
            if node.type == "property_declaration":
                body_node = node.child_by_field_name('accessor_list')
        
        if body_node:
            body = body_node.text.decode('utf-8')
            
            cursor = QueryCursor(self._dep_query)
            matches = cursor.matches(body_node)
            
            for _, match_dict in matches:
                dep_nodes = match_dict.get("dependencies")
                name_nodes = match_dict.get("name")
                
                if dep_nodes and name_nodes:
                    d_node = dep_nodes[0]
                    n_node = name_nodes[0]
                    
                    res = n_node.text.decode('utf-8')
                    # remove generics from invoked name if present
                    if '<' in res:
                        res = res.split('<')[0]
                    
                    identifier = res.split('.')[-1]
                    
                    dependency_names.append((
                        d_node.text.decode('utf-8'), 
                        identifier
                    ))
                            
        instance = CSharpMethod(
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

    def parse_field(self, node: Node, scope: str = "") -> CSharpField:
        type_text: str = ""
        modifiers: list[str] = []
        identifier: str = "Unknown"
        value: str = ""
        
        type_node = node.child_by_field_name('type')
        if type_node:
            type_text = type_node.text.decode('utf-8')

        for child in node.children:
            child_type = child.type
            if child_type == "modifier":
                modifiers.append(child.text.decode('utf-8'))
            elif child_type == "variable_declaration":
                # In C#, fields are usually variable_declaration
                t_node = child.child_by_field_name('type')
                if t_node:
                    type_text = t_node.text.decode('utf-8')
                for var_decl in child.children:
                    if var_decl.type == "variable_declarator":
                        name_node = var_decl.child_by_field_name('name')
                        if name_node:
                            identifier = name_node.text.decode('utf-8')
                        value_node = var_decl.child_by_field_name('value')
                        if value_node:
                            value = value_node.text.decode('utf-8')
                        break
        
        # If it wasn't captured gracefully (Grammar edge cases)
        if identifier == "Unknown":
            for child in node.children:
                if child.type == "variable_declarator":
                    name_node = child.child_by_field_name('name')
                    if name_node:
                        identifier = name_node.text.decode('utf-8')
                    value_node = child.child_by_field_name('value')
                    if value_node:
                        value = value_node.text.decode('utf-8')
                    break

        ucid = f"{scope}.{identifier}" if scope else identifier

        access = "private"
        other_mods = []
        for mod in modifiers:
            if mod in CSharpClass.ACCESS_MODIFIERS:
                access = mod
            else:
                other_mods.append(mod)

        sig_parts = [access] + other_mods + [type_text, identifier]
        signature = " ".join(filter(None, sig_parts))
        
        if value:
            signature += f" = {value}"

        return CSharpField(
            ucid=ucid, 
            name=identifier, 
            signature=signature, 
            field_type=type_text
        )

