import os
import hashlib
import re
from typing import List, Dict, Any, Optional
from tree_sitter import Node, Query, QueryCursor, Parser

from toaster.languages.java.queries import DEPENDENCY_QUERY
from toaster.languages.java.language import JAVA_LANGUAGE
from toaster.core import BaseFile, BaseClass, BaseMethod, BaseField, MemberRegistry

class JavaFile(BaseFile):
    def __init__(self, ufid: str, imports: list[str], classes: list["JavaClass"], registry: MemberRegistry = None):
        # BaseFile init: (ufid, imports, classes)
        super().__init__(ufid, imports, classes, registry)

    @classmethod
    def from_source(cls, filename: str, source_code: bytes, registry: MemberRegistry = None) -> "JavaFile":
        parser = Parser()
        parser.language = JAVA_LANGUAGE
        tree = parser.parse(source_code)
        root_node = tree.root_node
        
        scope = ""
        imports = []
        classes = []
        
        # if filename.endswith("Strictness.java"):
        #     print(root_node)


        for child in root_node.children:
            if child.type == "package_declaration":
                # package com.example; -> child[1] is the identifier
                for grandchild in child.children:
                    if grandchild.type in {"scoped_identifier", "identifier"}:
                        scope = grandchild.text.decode('utf-8')
                        break
            elif child.type == "import_declaration":
                # import java.util.List;
                for grandchild in child.children:
                    if grandchild.type in {"scoped_identifier", "identifier"}:
                        imports.append(grandchild.text.decode('utf-8'))
            elif child.type == "class_declaration" or child.type == "interface_declaration":
                java_class = JavaClass.from_node(child, scope, registry=registry)
                classes.append(java_class)
                registry.add_class(java_class)
            elif child.type == "enum_declaration":
                java_enum = JavaEnum.from_node(child, scope, registry=registry)
                classes.append(java_enum)
                registry.add_class(java_enum)

        return cls(filename, imports, classes, registry)

    @classmethod
    def from_file(cls, filepath: str, registry: MemberRegistry = None) -> "JavaFile":
        with open(filepath, "rb") as f:
            source = f.read()
        return cls.from_source(os.path.basename(filepath), source, registry)


class JavaClass(BaseClass):
    
    ACCESS_MODIFIERS = {"public", "protected", "private"}

    def __init__(self, ucid: str, signature: str, body: str, node: "Node" = None, registry: MemberRegistry = None):
        # BaseClass init: (ucid, signature, body)
        super().__init__(ucid, signature, body, node, registry)
        
        # Override types for Java specifics if needed, but Base dicts work fine
        self.fields: Dict[str, "JavaField"] = {}
        self.methods: Dict[str, "JavaMethod"] = {}
        self.child_classes: Dict[str, "JavaClass"] = {}
        

    @classmethod
    def from_node(cls, node: "Node", scope: str = "", registry: MemberRegistry = None) -> "JavaClass":
        
        identifier: str = ""
        superclass: str = ""
        modifiers: List[str] = []
        interfaces: List[str] = []
        type_params: List[str] = []
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

        # Construct Signature
        access = "package-private"
        is_interface = node.type == "interface_declaration"
        other_mods = []
        
        for mod in modifiers:
            if mod in cls.ACCESS_MODIFIERS:
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

        instance = cls(ucid, signature, final_body, node, registry)
        

        # Parse Body
        if body_node:
            for child in body_node.children:
                ct = child.type
                
                if ct in ("method_declaration", "constructor_declaration"):
                    method = JavaMethod.from_node(child, instance.ucid, registry=registry)
                    instance.methods[method.umid] = method
                    registry.add_method(method)
                    
                elif ct == "field_declaration":
                    field = JavaField.from_node(child, instance.ucid)
                    instance.fields[field.ucid] = field
                    
                elif ct == "class_declaration" or ct == "interface_declaration":
                    child_class = JavaClass.from_node(child, instance.ucid, registry=registry)
                    instance.child_classes[child_class.ucid] = child_class
                elif ct == "enum_declaration":
                    child_class = JavaEnum.from_node(child, instance.ucid, registry=registry)
                    instance.child_classes[child_class.ucid] = child_class

        return instance
    
    def skeletonize(self) -> str:
        replacements = []
        
        class_start_byte = self.node.start_byte
        
        for method in self.methods.values():
            method_node = method.node
            method_description = method.description
            
            if not method_description:
                continue
            
            body_node = None
            for child in method_node.children:
                if child.type == 'block':
                    body_node = child
                    break
            if body_node:
                rel_start = body_node.start_byte - class_start_byte
                rel_end = body_node.end_byte - class_start_byte
                replacements.append({
                    "start": rel_start,
                    "end": rel_end,
                    "text": f"{{\n    // {method_description}\n    }}"
                })
        replacements.sort(key=lambda x: x["start"], reverse=True)
        
        modified_source = self.node.text
        for rep in replacements:
            # Slice the byte string: [everything before body] + [new body] + [everything after body]
            modified_source = (
                modified_source[:rep["start"]] + 
                rep["text"].encode('utf-8') + 
                modified_source[rep["end"]:]
            )

        return modified_source.decode('utf-8')


class JavaField(BaseField):
    
    ACCESS_MODIFIERS = {"public", "protected", "private"}

    def __init__(self, ucid: str, name: str, signature: str, field_type: str):
        # BaseField init: (ucid, name, signature)
        super().__init__(ucid, name, signature, field_type)

    @classmethod
    def from_node(cls, node: "Node", scope: str = "") -> "JavaField":
        type_text: str = ""
        modifiers: List[str] = []
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

        # ucid: "com.example.MyClass.myField"
        ucid = f"{scope}.{identifier}" if scope else identifier

        access = "package-private"
        other_mods = []
        for mod in modifiers:
            if mod in cls.ACCESS_MODIFIERS:
                access = mod
            else:
                other_mods.append(mod)

        sig_parts = [access] + other_mods + [type_text, identifier]
        signature = " ".join(filter(None, sig_parts))
        
        if value:
            signature += f" = {value}"

        return cls(ucid, identifier, signature, type_text)


class JavaMethod(BaseMethod):
    
    _DEP_QUERY = Query(JAVA_LANGUAGE, DEPENDENCY_QUERY)
    ACCESS_MODIFIERS = {"public", "protected", "private"}
    
    def __init__(self, identifier: str, scoped_identifier: str, return_type: str, umid: str, signature: str, body: str, body_hash: str, 
                 dependency_names: List[str], line: int, parameters: List[str], node:"Node" = None, registry: MemberRegistry = None):
        # BaseMethod init: (umid, signature, body, body_hash, dependency_names)
        super().__init__(identifier, scoped_identifier, return_type, umid, signature, body, body_hash, dependency_names, line, parameters, node, registry)
    
    @classmethod
    def from_node(cls, node: "Node", scope: str, dep_query: "Query" = None, registry: MemberRegistry = None) -> "JavaMethod":
        line = node.start_point[0]
        
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
        params_types = []
        
        params_node = node.child_by_field_name('parameters')
        if params_node:
            for child in params_node.children:
                if child.type in ("formal_parameter", "spread_parameter"):
                    params_full.append(child.text.decode('utf-8'))
                    
                    t_node = child.child_by_field_name('type')
                    if t_node:
                        params_types.append(t_node.text.decode('utf-8'))
                    else:
                        params_types.append(child.text.decode('utf-8').split()[0])
        
        
        
        # UMID Construction
        umid = f"{scope}#{identifier}({','.join(params_types)})"
        scoped_identifier = f"{scope}.{identifier}"
        
        modifiers = []
        throws_clause = ""
        type_params = ""
        
        for child in node.children:
            ct = child.type
            if ct == "modifiers":
                for mod_node in child.children:
                    if mod_node.type not in ['line_comment', 'block_comment', 'annotation', 'marker_annotation']:
                        modifiers.append(mod_node.text.decode('utf-8'))
                # print(modifiers)
                
            elif ct == "type_parameters":
                type_params = child.text.decode('utf-8')
            elif ct == "throws":
                throws_clause = child.text.decode('utf-8')
                
        access = "package-private"
        other_mods = []
        for mod in modifiers:
            if mod in cls.ACCESS_MODIFIERS:
                access = mod
            else:
                if mod:
                    other_mods.append(mod)
        
        sig_parts = [access] + other_mods + [return_type, identifier, type_params]
        if return_type == "void" and node.type == 'constructor_declaration':
            sig_parts.remove("void")
            return_type = "<constructor>"
             
        full_sig_str = f"{' '.join(filter(None, sig_parts))}({', '.join(params_full)})"
        if throws_clause:
            full_sig_str += f" {throws_clause}"
        
        
        body = ""
        body_hash = ""
        dependency_names = []

        body_node = node.child_by_field_name('body')
        if body_node:
            body = body_node.text.decode('utf-8')
            clean_body = re.sub(r'\s+', '', body)
            body_hash = hashlib.sha256(clean_body.encode('utf-8')).hexdigest()[:8]
            
            # Use class level query if none provided
            cursor = QueryCursor(JavaMethod._DEP_QUERY)
            
            captures = cursor.captures(body_node)
            # Tree-sitter python bindings vary by version. 
            # This handles the common case: dict of {name: [nodes]}
            if isinstance(captures, dict) and "dependencies" in captures:
                for d_node in captures["dependencies"]:
                    dependency_names.append(d_node.text.decode('utf-8'))
            # Handle list of tuples case [(node, name)]
            elif isinstance(captures, list):
                for d_node, name in captures:
                    if name == "dependencies":
                        dependency_names.append(d_node.text.decode('utf-8'))
                            
        return cls(identifier, scoped_identifier, return_type, umid, full_sig_str, body, body_hash, dependency_names, line, parameters=params_full, node=node, registry=registry)
    
    def resolve_dependencies(self, imports: List[str]) -> None:
            
        if not self.dependency_names:
            return
        
        unique_names = set(self.dependency_names)
        
        if '#' in self.umid:
            parent_class = self.umid.split('#')[0]
        else:
            parent_class = self.umid.rsplit('.', 1)[0]
        
        
        
        for name in unique_names:
            param_str = name.split('(')[-1].strip(')')
            arity = 0 if param_str == '' else len(param_str.split(','))
            # 1. Local Check
            local_fullname = f"{parent_class}.{name}"
            if local_fullname in self.registry.map_scoped:
                candidates = [c for c in self.registry.map_scoped[local_fullname] if c.arity == arity]
                if len(candidates) == 1:
                    candidates[0].inbound_dependencies.append(f"#{self.umid.split('#')[-1]}")
                    self.dependencies.append(f"#{candidates[0].umid.split('#')[-1]}")
                else:
                    for candidate in candidates: 
                        candidate.inbound_dependencies.append(f"~#{self.umid.split('#')[-1]}")
                    if len(candidates) <= 3:
                        self.dependencies.extend([f"~#{c.umid.split('#')[-1]}" for c in candidates])    
                    else:
                        self.dependencies.append(f"~#{candidates[0].identifier}(?)")
                continue
            
            # 2. Import Check
            resolved_via_import = False
            candidates = []
            for imp in imports:
                import_fullname = f"{imp}.{name}"
                if import_fullname in self.registry.map_scoped:
                    candidates.extend(self.registry.map_scoped[import_fullname])
            if candidates:
                if len(candidates) == 1:
                    candidates[0].inbound_dependencies.append(self.umid)
                    self.dependencies.append(candidates[0].umid)
                else:
                    for c in candidates: c.inbound_dependencies.append(f"~{self.umid}")
                    self.dependencies.extend([f"~{c.umid}" for c in candidates if c.arity == arity])
                continue
            
            # 3. Global Name Check
            if name in self.registry.map_short:
                candidates = [c for c in self.registry.map_short[name] if c.arity == arity]
                if len(candidates) == 1:
                    candidates[0].inbound_dependencies.append(self.umid)
                    self.dependencies.append(candidates[0].umid)
                else:
                    self.dependencies.extend([f"~{c.umid}" for c in candidates])
                    if len(candidates) <= 3:
                        for c in candidates: c.inbound_dependencies.append(f"~{self.umid}")
                    else:
                        self.dependencies.append(f"~{candidates[0].identifier}(?)")
                continue
            
            self.unresolved_dependencies.append(name)
        # remove duplicates
        self.dependencies = list(set(self.dependencies))
        self_ref = f"#{self.umid.split('#')[-1]}"
        self.dependencies = [d for d in self.dependencies if d != self_ref]


class JavaEnum(JavaClass):

    @classmethod
    def from_node(cls, node: "Node", scope: str = "", registry: MemberRegistry = None) -> "JavaEnum":
        identifier: str = ""
        modifiers: List[str] = []
        interfaces: List[str] = []
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

        # Signature Construction
        access = "package-private"
        other_mods = []
        for mod in modifiers:
            if mod in cls.ACCESS_MODIFIERS:
                access = mod
            else:
                other_mods.append(mod)

        sig_parts = [access] + other_mods + ["enum", identifier]
        if interfaces:
            sig_parts.append(f"implements {', '.join(interfaces)}")
        final_signature = " ".join(filter(None, sig_parts))
        
        final_body = body_node.text.decode('utf-8') if body_node else ""
        
        # Instantiate the object
        instance = cls(ucid, final_signature, final_body, node, registry)

        # Attach members (Constants, Methods, Fields)
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
                    method = JavaMethod.from_node(child, instance.ucid, registry=registry)
                    instance.methods[method.umid] = method
                    registry.add_method(method)
                    
                elif ct == "field_declaration":
                    field = JavaField.from_node(child, instance.ucid)
                    instance.fields[field.ucid] = field

        return instance